"""Build the static copy of arent.pl from crawled HTML pages.

Text pages (HTML) plus the CSS/JS/fonts they need are stored locally.
Images are NOT downloaded: an image is served locally only if it already
exists in the site folder (homepage), otherwise it stays a link to arent.pl.
Links between mirrored pages are rewritten to local relative paths.
Tracking (Google Analytics, Facebook Pixel/chat, Popup Maker stats) is removed.

Usage:
    python3 -I tools/fetchpages.py <crawl_dir> <urls.txt>
    python3 -I tools/build.py <site_dir> <crawl_dir>
"""
import base64, hashlib, html, json, os, posixpath, re, sys, urllib.parse, urllib.request

SITE = os.path.abspath(sys.argv[1])
CRAWL = os.path.abspath(sys.argv[2])
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
ASSET_HOSTS = {"arent.pl", "www.arent.pl", "fonts.googleapis.com", "fonts.gstatic.com"}
DL_EXT = (".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".json")

done, failed = {}, set()


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")


def is_asset(url):
    p = urllib.parse.urlsplit(url)
    if p.netloc not in ASSET_HOSTS:
        return False
    return p.netloc.startswith("fonts.") or p.path.startswith(("/wp-content/", "/wp-includes/"))


def local_path(url):
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
    """Return local path of the asset, downloading code/fonts if needed.
    Images and other media are never downloaded (None unless already present)."""
    url = urllib.parse.urldefrag(url)[0]
    if url.startswith("//"):
        url = "https:" + url
    if url in done:
        return done[url]
    if url in failed:
        return None
    lp = local_path(url)
    full = os.path.join(SITE, lp)
    downloadable = lp.lower().endswith(DL_EXT) or urllib.parse.urlsplit(url).netloc == "fonts.googleapis.com"
    if os.path.isfile(full):
        done[url] = lp
        return lp
    if not downloadable:
        return None
    try:
        data, ctype = fetch(url)
    except Exception as e:  # noqa
        print("FAIL", url, e, file=sys.stderr)
        failed.add(url)
        return None
    done[url] = lp
    if lp.endswith(".css") or "text/css" in ctype:
        data = rewrite_css(data.decode("utf-8", "replace"), url, lp).encode("utf-8")
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
        return f"url('{r}')" if m.group(2) is not None else f"@import '{r}'"
    return CSS_URL.sub(sub, text)


# ---------------------------------------------------------------- pages
pages = {}  # canonical url -> local html path
crawled = []
for fn in sorted(os.listdir(CRAWL)):
    with open(os.path.join(CRAWL, fn), encoding="utf-8") as f:
        req = f.readline().strip()
        final = f.readline().strip()
        body = f.read()
    path = urllib.parse.unquote(urllib.parse.urlsplit(final).path).strip("/")
    lp = (path + "/index.html") if path else "index.html"
    pages[final] = lp
    pages[req] = lp
    crawled.append((final, lp, body))


def page_target(url):
    u, frag = urllib.parse.urldefrag(url)
    if urllib.parse.urlsplit(u).query:
        return None
    if not u.endswith("/"):
        u += "/"
    for cand in (u, u.replace("://www.", "://")):
        if cand in pages:
            return pages[cand], frag
    return None


URL_RE = re.compile(r"""(?:https?:)?//(?:www\.)?(?:arent\.pl|fonts\.googleapis\.com|fonts\.gstatic\.com)(?:/[^\s"'<>()\\]*)?""")
ESC_URL = re.compile(r"(?:https?:)?\\?/\\?/(?:www\.)?arent\.pl\\?/(?:wp-content|wp-includes)(?:\\?/[^\s\"'\\<>]+)+\.(?:css|js|woff2?|ttf|eot|png|jpe?g|gif|webp|svg)")
TRACKERS = ("gtag(", "fbq(", "xfbml.customerchat", "connect.facebook.net")


def build(url, lp, page):
    page = re.sub(r'(href|action)="/(?!/)', r'\1="https://arent.pl/', page)
    page = re.sub(r"(<style[^>]*>)(.*?)(</style>)",
                  lambda m: m.group(1) + rewrite_css(m.group(2), url, lp) + m.group(3), page, flags=re.S)

    def sub(m):
        raw, tail = m.group(0), ""
        while raw.endswith((",", ";")) and not raw.endswith("&#038;"):
            tail, raw = raw[-1] + tail, raw[:-1]
        absu = html.unescape(raw)
        if absu.startswith("//"):
            absu = "https:" + absu
        if "{{" in absu:
            return raw + tail
        if is_asset(absu):
            target = download(absu)
            if target:
                return rel(lp, target) + tail
            return (raw if raw.startswith("http") else "https:" + raw) + tail
        t = page_target(absu)
        if t:
            r = rel(lp, t[0])
            return r + ("#" + t[1] if t[1] else "") + tail
        return raw + tail

    page = URL_RE.sub(sub, page)

    # Instagram feed: use local resized images only if all of them exist here
    insta_local = False
    for m in re.finditer(r'data-resized="([^"]+)"', page):
        items = json.loads(html.unescape(m.group(1))).values()
        insta_local = all(
            os.path.isfile(os.path.join(SITE, "wp-content/uploads/sb-instagram-feed-images",
                                        it["id"] + s + it.get("extension", ".jpg")))
            for it in items for s in it.get("sizes", {}))
    insta_rel = rel(lp, "wp-content/uploads/sb-instagram-feed-images/x")[:-1]

    def fix_js(js):
        if any(t in js for t in TRACKERS):
            return "/* tracking removed in static copy */"

        def esc(m):
            raw = m.group(0)
            u = raw.replace("\\/", "/")
            target = download("https:" + u if u.startswith("//") else u)
            if not target:
                return raw
            r = rel(lp, target)
            return r.replace("/", "\\/") if "\\/" in raw else r
        js = ESC_URL.sub(esc, js)
        if insta_local:
            js = js.replace('"resized_url":"https://arent.pl/wp-content/uploads/sb-instagram-feed-images/"',
                            f'"resized_url":"{insta_rel}"')
        return js.replace('"disable_tracking":""', '"disable_tracking":"1"').replace(
            '"analytics_enabled":"1"', '"analytics_enabled":""')

    page = re.sub(r"data:text/javascript;base64,([A-Za-z0-9+/=]+)",
                  lambda m: "data:text/javascript;base64," + base64.b64encode(
                      fix_js(base64.b64decode(m.group(1)).decode("utf-8")).encode()).decode(), page)
    page = re.sub(r"<script(?![^>]*\bsrc=)[^>]*>(?:(?!</script>).)*?GoogleAnalyticsObject.*?</script>", "", page, flags=re.S)
    page = re.sub(r"<script[^>]*googletagmanager\.com[^>]*></script>", "", page)
    page = re.sub(r'<div class="fb-customerchat"[^>]*></div>', "", page)
    page = re.sub(r"<noscript><img[^>]*facebook\.com/tr[^>]*/?></noscript>", "", page)

    full = os.path.join(SITE, lp)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(page)


for i, (url, lp, body) in enumerate(crawled):
    build(url, lp, body)
print(f"{len(crawled)} pages, {len(done)} assets referenced locally, {len(failed)} failed")
for u in sorted(failed):
    print("  failed:", u)
