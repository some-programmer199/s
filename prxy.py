from quart import Quart, request, Response, abort
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
from functools import lru_cache
import time

app = Quart(__name__)

PROXY_PATH = "/proxy?url="
CACHE_TTL = 60  # seconds

# Simple in-memory cache: {url: (html, timestamp)}
cache = {}
cache_lock = asyncio.Lock()

async def fetch_html(url):
    """Fetch raw HTML from the target site with timeout and headers."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status != 200:
                    return f"<h1>Error {resp.status} loading {url}</h1>"
                return await resp.text()
    except Exception as e:
        return f"<h1>Failed to fetch {url}: {e}</h1>"

def rewrite_links(html, base_url):
    """Rewrite all href/src/action links to route through the proxy."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "link", "script", "img", "form"]):
        attr = None
        if tag.name in ["a", "link"]: attr = "href"
        elif tag.name in ["script", "img"]: attr = "src"
        elif tag.name == "form": attr = "action"

        if attr and tag.has_attr(attr):
            url = tag[attr]
            if url.startswith("#") or url.startswith("javascript:"):
                continue
            absolute_url = urljoin(base_url, url)
            tag[attr] = f"{PROXY_PATH}{absolute_url}"

    # Optional: inject <base> tag to help relative paths
    if soup.head:
        base_tag = soup.new_tag("base", href=base_url)
        soup.head.insert(0, base_tag)

    return str(soup)

async def get_cached_html(url):
    """Return cached HTML if valid, else fetch and cache it."""
    async with cache_lock:
        now = time.time()
        if url in cache:
            html, timestamp = cache[url]
            if now - timestamp < CACHE_TTL:
                return html
        html = await fetch_html(url)
        html = rewrite_links(html, url)
        cache[url] = (html, now)
        return html

@app.route("/")
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Headful Proxy Demo</title></head>
    <body>
        <h1>Headful Proxy Server</h1>
        <input id="url" placeholder="Enter URL" style="width:300px"/>
        <button onclick="fetchPage()">Fetch</button>
        <div id="output" style="border:1px solid #ccc; margin-top:10px; padding:10px;"></div>

        <script>
            async function fetchPage(url=null) {
                if (!url) url = document.getElementById('url').value;
                const response = await fetch(`/proxy?url=${encodeURIComponent(url)}`);
                const html = await response.text();
                document.getElementById('output').innerHTML = html;
            }

            document.addEventListener('click', async (e) => {
                const target = e.target.closest('a');
                if (target && target.href.includes('/proxy?url=')) {
                    e.preventDefault();
                    fetchPage(target.href.split('url=')[1]);
                }
            });
        </script>
    </body>
    </html>
    """

@app.route("/proxy")
async def proxy():
    url = request.args.get("url")
    if not url or not url.startswith("http"):
        return abort(400, "Invalid URL")

    html = await get_cached_html(url)
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
