from flask import Flask, request
from downloader import download_url
import os

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path=""
)

@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/convert")
def convert_video():
    url = request.args.get("url")
    
    if not url:
        return "No url provided.", 404
    
    try:
        title = download_url(url)
        return f"Downloaded: {title}"
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)