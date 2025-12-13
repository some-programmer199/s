from bs4 import BeautifulSoup
from urllib.parse import urljoin

def rewrite_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "link", "script", "img", "form"]):
        attr = "href" if tag.name in ["a", "link"] else "src" if tag.name in ["script", "img"] else "action" if tag.name == "form" else None
        if attr and tag.get(attr) and tag[attr].startswith("http"):
            tag[attr] = "/?" + tag[attr]  # Lazy encode

    # Install service worker for stealth routing
    sw = soup.new_tag("script")
    sw.string = """
    navigator.serviceWorker.register('/static/sw.js').catch(console.error);
    """
    soup.body.append(sw)

    return str(soup)
