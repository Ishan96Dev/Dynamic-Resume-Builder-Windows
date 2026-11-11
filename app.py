# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""Flask backend for the Windows desktop app (launched via main.py).

Author: Ishan Chakraborty
License: MIT
"""
import base64
import re

from flask import Flask, jsonify, render_template, request, send_file

from resume_builder import build_resume

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not str(payload.get("name", "")).strip():
        return jsonify(error="Full name is required."), 400

    photo = None
    photo_data = payload.get("photo")
    if isinstance(photo_data, str) and photo_data.startswith("data:image"):
        try:
            photo = base64.b64decode(photo_data.split(",", 1)[1])
        except Exception:
            photo = None

    buf = build_resume(payload, photo)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", payload["name"].strip()).strip("_") or "Resume"
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{safe}_Resume.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )




