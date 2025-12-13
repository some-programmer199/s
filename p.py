import aiohttp
from aiohttp import web
from urllib.parse import urlparse, urljoin
import asyncio

routes = web.RouteTableDef()

TARGET_HOST = "chatgpt.com"  # Optional default host if you want
BLACKLISTED_HEADERS = [
    "Host",
    "Content-Length",
    "Accept-Encoding",  # allow aiohttp to handle compression
    "Connection",
]

@routes.route("*", "/{tail:.*}")
async def proxy_handler(request):
    # Determine target URL
    path = request.match_info["tail"]
    query = request.query_string

    # Use full URL if path includes scheme (proxy style: /https://site.com/...)
    if path.startswith("http://") or path.startswith("https://"):
        target_url = f"{path}?{query}" if query else path
    else:
        # Optional: default target host (not needed if always sending full URL)
        target_url = f"https://{TARGET_HOST}/{path}?{query}" if query else f"https://{TARGET_HOST}/{path}"

    # Prepare headers
    headers = {k: v for k, v in request.headers.items() if k not in BLACKLISTED_HEADERS}

    # Read body if present
    body = await request.read() if request.can_read_body else None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method,
                target_url,
                headers=headers,
                data=body,
                allow_redirects=False,
                timeout=15
            ) as resp:
                # Stream response body
                response_headers = {k: v for k, v in resp.headers.items() if k.lower() != "transfer-encoding"}
                response_body = await resp.read()
                return web.Response(body=response_body, status=resp.status, headers=response_headers)
    except Exception as e:
        return web.Response(text=f"Error fetching {target_url}: {e}", status=500)

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)