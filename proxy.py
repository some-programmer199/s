from flask import Flask, request, Response, abort
import asyncio
from playwright.async_api import async_playwright, Page
import threading
import io

app = Flask(__name__)

# Globals
browser = None
playwright_instance = None
loop = asyncio.new_event_loop()
loop_thread = None
lock = threading.Lock()

# Start asyncio loop in background thread
def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Initialize persistent browser
def startup():
    global browser, playwright_instance, loop_thread
    loop_thread = threading.Thread(target=start_event_loop, args=(loop,), daemon=True)
    loop_thread.start()

    async def init_browser():
        global browser, playwright_instance
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(headless=True)
    asyncio.run_coroutine_threadsafe(init_browser(), loop).result()

# Shutdown browser
def shutdown():
    global browser, playwright_instance
    async def close_browser():
        if browser:
            await browser.close()
        if playwright_instance:
            await playwright_instance.stop()
    asyncio.run_coroutine_threadsafe(close_browser(), loop).result()

# Root page with client interface
@app.route("/")
def index():
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
def proxy():
    url = request.args.get("url")
    if not url or not url.startswith("http"):
        return abort(400, "Invalid URL")

    async def fetch_page(url):
        page: Page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            return content
        finally:
            await page.close()

    future = asyncio.run_coroutine_threadsafe(fetch_page(url), loop)
    content = future.result()
    return Response(io.BytesIO(content.encode("utf-8")), mimetype="text/html")

if __name__ == "__main__":
    startup()
    try:
        app.run(host="0.0.0.0", port=8000, debug=True)
    finally:
        shutdown()
