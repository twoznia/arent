"""Second pass over the mirrored index.html.

- localises asset URLs hidden in base64 data: scripts (slider JSON, Instagram feed)
- downloads Instagram feed images listed in data-resized
- removes tracking (Google Analytics / gtag, Facebook Pixel, Facebook chat)
Usage: python3 -I postprocess.py <site_dir>
"""
import base64, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror  # noqa: E402

SITE = os.path.abspath(sys.argv[1])
mirror.OUT = SITE
INDEX = os.path.join(SITE, "index.html")
s = open(INDEX, encoding="utf-8").read()

ESC_URL = re.compile(r"(?:https?:)?\\?/\\?/(?:www\.)?arent\.pl\\?/(?:wp-content|wp-includes)(?:\\?/[^\s\"'\\<>]+)+\.(?:png|jpe?g|gif|webp|svg|css|js|woff2?|ttf|eot|mp4)")


def localise_escaped(js):
    def sub(m):
        raw = m.group(0)
        url = raw.replace("\\/", "/")
        if url.startswith("//"):
            url = "https:" + url
        target = mirror.download(url)
        if not target:
            return raw
        return target.replace("/", "\\/") if "\\/" in raw else target
    return ESC_URL.sub(sub, js)


TRACKERS = ("gtag(", "fbq(", "xfbml.customerchat", "connect.facebook.net")


def fix_data_script(m):
    js = base64.b64decode(m.group(1)).decode("utf-8")
    if any(t in js for t in TRACKERS):
        js = "/* tracking removed in static copy */"
    js = localise_escaped(js)
    js = js.replace('"resized_url":"https://arent.pl/wp-content/uploads/sb-instagram-feed-images/"',
                    '"resized_url":"wp-content/uploads/sb-instagram-feed-images/"')
    js = js.replace('"disable_tracking":""', '"disable_tracking":"1"').replace('"analytics_enabled":"1"', '"analytics_enabled":""')
    return "data:text/javascript;base64," + base64.b64encode(js.encode("utf-8")).decode()


s = re.sub(r"data:text/javascript;base64,([A-Za-z0-9+/=]+)", fix_data_script, s)

# Inline Google Analytics + gtag loader + Facebook chat container
s = re.sub(r"<script(?![^>]*\bsrc=)[^>]*>(?:(?!</script>).)*GoogleAnalyticsObject.*?</script>", "", s, flags=re.S)
s = re.sub(r"<script[^>]*googletagmanager\.com[^>]*></script>", "", s)
s = re.sub(r'<div class="fb-customerchat"[^>]*></div>', "", s)
s = re.sub(r"<noscript><img[^>]*facebook\.com/tr[^>]*/?></noscript>", "", s)

# Instagram feed resized images
n = 0
for m in re.finditer(r'data-resized="([^"]+)"', s):
    data = json.loads(html.unescape(m.group(1)))
    for item in data.values():
        ext = item.get("extension", ".jpg")
        for size in item.get("sizes", {}):
            url = f"https://arent.pl/wp-content/uploads/sb-instagram-feed-images/{item['id']}{size}{ext}"
            if mirror.download(url):
                n += 1

open(INDEX, "w", encoding="utf-8").write(s)
print("instagram images:", n, "extra downloads:", len(mirror.done), "failed:", sorted(mirror.failed))
