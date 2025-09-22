# keep_alive.py
import time
import threading
from flask import Flask, jsonify

_start_time = time.time()
app = Flask("keep-alive")

@app.route("/")
def index():
    return "ok", 200

@app.route("/health")
def health():
    uptime_seconds = int(time.time() - _start_time)
    return jsonify({
        "status": "ok",
        "uptime_seconds": uptime_seconds
    }), 200

def _run():
    # Force port 8080 for Replit public access
    app.run(host="0.0.0.0", port=8080, threaded=True)

def keep_alive():
    """Call this function once at startup to spawn the webserver in a daemon thread."""
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    
