from flask import Flask, request, Response, send_from_directory
import requests
from rewrite import rewrite_html

app = Flask(__name__)

TARGET = "https://chatgpt.com"  # You can change dynamically later

@app.route("/")
def index():
    resp = requests.get(TARGET, headers={'User-Agent': request.headers.get('User-Agent')})
    content = rewrite_html(resp.text)
    return Response(content, mimetype="text/html")

@app.route("/<path:path>", methods=["GET", "POST"])
def proxy(path):
    url = f"{TARGET}/{path}"
    if request.method == "POST":
        resp = requests.post(url, data=request.form, headers={'User-Agent': request.headers.get('User-Agent')})
    else:
        resp = requests.get(url, headers={'User-Agent': request.headers.get('User-Agent')})

    ctype = resp.headers.get("Content-Type", "")
    if "text/html" in ctype:
        content = rewrite_html(resp.text)
        return Response(content, mimetype="text/html")
    return Response(resp.content, content_type=ctype)

@app.route("/static/<path:path>")
def sw(path):
    return send_from_directory("static", path)

app.run(host="127.0.0.1", port=5000)
