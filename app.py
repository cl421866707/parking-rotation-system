"""Flask entry: static UI + JSON API for parking rotation lottery."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from lottery.engine import (
    DrawError,
    bootstrap,
    perform_draw,
    preview_pools,
    undo_last,
)
from lottery.models import ConfigError, DataStore

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
store = DataStore(ROOT)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/bootstrap")
def api_bootstrap():
    return jsonify(bootstrap(store))


@app.put("/api/config")
def api_config():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "请求体必须是 JSON 对象"}), 400
    try:
        config = store.save_config(payload)
    except ConfigError as e:
        return jsonify({"error": str(e)}), 400
    data = bootstrap(store)
    data["config"] = config
    return jsonify(data)


@app.get("/api/pools")
def api_pools():
    return jsonify(preview_pools(store))


@app.post("/api/draw")
def api_draw():
    try:
        result = perform_draw(store)
    except (DrawError, ConfigError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(
        {
            "entry": result["entry"],
            "state": result["state"],
            "history": result["history"],
            "config": result["config"],
            "pools": preview_pools(store)["pools"],
            "next_period_number": result["state"]["draw_count"] + 1,
        }
    )


@app.get("/api/history")
def api_history():
    _, _, history = store.load_all()
    return jsonify({"history": history})


@app.post("/api/history/undo")
def api_undo():
    try:
        result = undo_last(store)
    except DrawError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(
        {
            "undone": result["undone"],
            "state": result["state"],
            "history": result["history"],
            "config": result["config"],
            "pools": result["pools"],
            "next_period_number": int(result["state"].get("draw_count", 0)) + 1,
        }
    )


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
