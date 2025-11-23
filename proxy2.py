from quart import Quart, request, Response, abort
from playwright.async_api import async_playwright, Page
import asyncio
import io
from html import escape

app = Quart(__name__)

# Globals
browser = None
playwright_instance = None
# new globals
shared_context = None
semaphore = asyncio.Semaphore(4)  # tune concurrency to match container resources

# Startup: initialize Playwright
@app.before_serving
async def startup():
    global browser, playwright_instance, shared_context
    playwright_instance = await async_playwright().start()
    # run Chromium in containers with no-sandbox; add other args if needed
    browser = await playwright_instance.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    # create a shared context to reuse across requests (cheap to create pages from)
    shared_context = await browser.new_context()
    # be faster: don't wait for all network activity by default
    shared_context.set_default_navigation_timeout(10_000)
    shared_context.set_default_timeout(10_000)

    # block heavy/unnecessary resource types to speed loads
    async def _route_handler(route, request):
        if request.resource_type in ("image", "stylesheet", "font", "media", "websocket"):
            await route.abort()
        else:
            await route.continue_()

    await shared_context.route("**/*", _route_handler)

# Shutdown: close Playwright
@app.after_serving
async def shutdown():
    global browser, playwright_instance, shared_context
    if shared_context:
        await shared_context.close()
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
        <input id="url" placeholder="Enter URL" style="width:60%"/>
        <button onclick="loadPage()">Open in viewer</button>
        <button onclick="openNewTab()">Open in new tab</button>

        <div style="margin-top:10px;">
            <iframe id="viewer" style="width:100%; height:75vh; border:1px solid #ccc;"></iframe>
        </div>

        <script>
            function loadPage() {
                const url = document.getElementById('url').value;
                document.getElementById('viewer').src = `/proxy?url=${encodeURIComponent(url)}`;
            }
            function openNewTab() {
                const url = document.getElementById('url').value;
                window.open(`/proxy?url=${encodeURIComponent(url)}`, '_blank');
            }
        </script>
    </body>
    </html>
    """

# Proxy endpoint
@app.route("/proxy")
async def proxy():
    from urllib.parse import urlparse

    url = request.args.get("url", "")
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return abort(400, "Invalid URL")

    # throttle concurrency to avoid OOM / too many pages
    await semaphore.acquire()
    page: Page = await shared_context.new_page()
    try:
        # use domcontentloaded for faster HTML-only fetches; switch to "networkidle" for full JS execution on server
        await page.goto(url, wait_until="domcontentloaded", timeout=10_000)
        content = await page.content()

        # ensure relative URLs work when the browser loads this HTML: inject a <base> tag
        # use a simple replace to insert base into the first <head> tag if present
        base_tag = f'<base href="{escape(url)}">'
        if "<head" in content:
            # insert base right after the opening <head ...> tag
            import re
            content = re.sub(r"(?i)<head([^>]*)>", lambda m: f"<head{m.group(1)}>{base_tag}", content, count=1)
        else:
            # fall back to prepending base tag
            content = base_tag + content

        return Response(content, mimetype="text/html")
    except Exception:
        return abort(500, "Failed to fetch page")
    finally:
        try:
            await page.close()
        except Exception:
            pass
        semaphore.release()

if __name__ == "__main__":
    # Run Quart server
    app.run(host="0.0.0.0", port=8000)
