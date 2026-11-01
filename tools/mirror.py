"""Mirror the arent.pl homepage with all its assets into a static folder.

Usage: python3 -I mirror.py <output_dir>
"""
import hashlib, html, os, re, sys, urllib.parse, urllib.request, posixpath

OUT = os.path.abspath(sys.argv[1])
START = "https://arent.pl/"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
ASSET_HOSTS = {"arent.pl", "www.arent.pl", "fonts.googleapis.com", "fonts.gstatic.com"}

done = {}      # absolute url (no fragment) -> local relative path (posix, from OUT)
failed = set()


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")


def is_asset(url):
    p = urllib.parse.urlsplit(url)
    if p.netloc not in ASSET_HOSTS:
        return False
    if p.netloc.startswith("fonts."):
        return True
    return p.path.startswith(("/wp-content/", "/wp-includes/"))


def local_path(url, ctype=""):
    p = urllib.parse.urlsplit(url)
    if p.netloc == "fonts.googleapis.com":
        h = hashlib.md5(url.encode()).hexdigest()[:10]
        return f"assets/fonts.googleapis.com/{p.path.strip('/').replace('/', '_') or 'css'}-{h}.css"
    if p.netloc == "fonts.gstatic.com":
        return "assets/fonts.gstatic.com" + urllib.parse.unquote(p.path)
    return urllib.parse.unquote(p.path).lstrip("/")


def rel(from_file, to_file):
    r = posixpath.relpath(to_file, posixpath.dirname(from_file) or ".")
    return urllib.parse.quote(r, safe="/._-~%")


def download(url):
    """Download asset (recursively for CSS), return local path or None."""
    url = urllib.parse.urldefrag(url)[0]
    if url in done:
        return done[url]
    if url in failed:
        return None
    try:
        data, ctype = fetch(url)
    except Exception as e:  # noqa
        print("FAIL", url, e, file=sys.stderr)
        failed.add(url)
        return None
    lp = local_path(url, ctype)
    done[url] = lp
    if lp.endswith(".css") or "text/css" in ctype:
        text = data.decode("utf-8", "replace")
        text = rewrite_css(text, url, lp)
        data = text.encode("utf-8")
    full = os.path.join(OUT, lp)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    return lp


CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3""")


def rewrite_css(text, base_url, lp):
    def sub(m):
        raw = m.group(2) or m.group(4)
        if raw.startswith(("data:", "#", "{{")):
            return m.group(0)
        absu = urllib.parse.urljoin(base_url, raw.strip())
        if not is_asset(absu):
            return m.group(0)
        target = download(absu)
        if not target:
            return m.group(0).replace(raw, absu)
        r = rel(lp, target)
        if m.group(2) is not None:
            return f"url('{r}')"
        return f"@import '{r}'"
    return CSS_URL.sub(sub, text)


HTML_URL = re.compile(r"""(?:https?:)?//(?:www\.)?(?:arent\.pl|fonts\.googleapis\.com|fonts\.gstatic\.com)/[^\s"'<>()\\]*""")


def main():
    data, _ = fetch(START)
    page = data.decode("utf-8")
    lp = "index.html"

    # Root-relative page links -> live site (they are dynamic shop actions)
    page = re.sub(r'(href|action)="/(?!/)', r'\1="https://arent.pl/', page)

    # Inline <style> blocks and style="" attributes: CSS url() rewriting
    page = re.sub(r"(<style[^>]*>)(.*?)(</style>)",
                  lambda m: m.group(1) + rewrite_css(m.group(2), START, lp) + m.group(3),
                  page, flags=re.S)

    def sub(m):
        raw = m.group(0)
        tail = ""
        while raw.endswith((",", ";")) and not raw.endswith("&#038;"):
            tail = raw[-1] + tail
            raw = raw[:-1]
        url = html.unescape(raw)
        if url.startswith("//"):
            url = "https:" + url
        if "{{" in url or not is_asset(url):
            return raw + tail
        target = download(url)
        return (rel(lp, target) if target else raw) + tail

    page = HTML_URL.sub(sub, page)

    # Neutralise WordPress admin-bar/emoji style links that point to the live server API
    with open(os.path.join(OUT, lp), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"downloaded {len(done)} files, failed {len(failed)}")
    for u in sorted(failed):
        print("  failed:", u)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    main()
