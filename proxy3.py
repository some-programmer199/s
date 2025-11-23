from quart import Quart, request, Response, abort
from playwright.async_api import async_playwright, Page
import asyncio
import io

app = Quart(__name__)

# Globals
browser = None
playwright_instance = None
page_pool = asyncio.Queue()  # pool of pages
POOL_SIZE = 3  # number of pages to reuse

# Startup: initialize Playwright and fill page pool
@app.before_serving
async def startup():
    global browser, playwright_instance
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(headless=True)

    # create a pool of pages
    for _ in range(POOL_SIZE):
        page = await browser.new_page()
        await page_pool.put(page)

# Shutdown: close Playwright
@app.after_serving
async def shutdown():
    global browser, playwright_instance
    # close all pages
    while not page_pool.empty():
        page = await page_pool.get()
        await page.close()
    if browser:
        await browser.close()
    if playwright_instance:
        await playwright_instance.stop()

# Root page
@app.route("/")
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Playwright Proxy Demo</title></head>
    <body>
        <h1>Playwright Proxy Server</h1>
        <input id="url" placeholder="Enter URL" style="width:300px"/>
        <button onclick="fetchPage()">Fetch</button>
        <div id="output" style="border:1px solid #ccc; margin-top:10px; padding:10px;"></div>
        <script>
            async function fetchPage() {
                const url = document.getElementById('url').value;
                const response = await fetch(`/proxy?url=${encodeURIComponent(url)}`);
                const html = await response.text();
                document.getElementById('output').innerHTML = html;
            }
        </script>
    </body>
    </html>
    """

# Proxy endpoint
@app.route("/proxy")
async def proxy():
    url = request.args.get("url")
    if not url or not url.startswith("http"):
        return abort(400, "Invalid URL")

    # get a free page from the pool
    page: Page = await page_pool.get()
    try:
        # faster load: only wait for DOM content
        await page.goto(url, wait_until="domcontentloaded")
        content = await page.content()
        return Response(io.BytesIO(content.encode("utf-8")), mimetype="text/html")
    finally:
        # return the page back to the pool
        await page_pool.put(page)

if __name__ == "__main__":
    # Run Quart server
    app.run(host="0.0.0.0", port=8000)