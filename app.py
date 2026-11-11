# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""Flask backend for the Windows desktop app (launched via main.py).

Author: Ishan Chakraborty
License: MIT
"""
import base64
import os
import re
import secrets

import requests
from flask import (Flask, jsonify, redirect, render_template, request,
                   send_file, session)

from resume_builder import build_resume, linkedin

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 24 * 1024 * 1024  # LinkedIn export zips can be large
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)


@app.route("/")
def index():
    return render_template("index.html", linkedin_oauth=linkedin.is_configured())


@app.route("/auth/linkedin")
def linkedin_login():
    if not linkedin.is_configured():
        return "LinkedIn OAuth is not configured. See README.", 503
    session["li_state"] = secrets.token_urlsafe(24)
    return redirect(linkedin.authorization_url(session["li_state"]))


@app.route("/auth/linkedin/callback")
def linkedin_callback():
    expected = session.pop("li_state", None)
    if request.args.get("error") or not expected or request.args.get("state") != expected:
        return redirect("/?linkedin=error")
    try:
        session["li_profile"] = linkedin.fetch_profile(request.args.get("code", ""))
    except (requests.RequestException, KeyError):
        return redirect("/?linkedin=error")
    return redirect("/?linkedin=ok")


@app.route("/api/linkedin/profile")
def linkedin_profile():
    return jsonify(session.pop("li_profile", None) or {})


@app.route("/api/linkedin/import", methods=["POST"])
def linkedin_import():
    f = request.files.get("file")
    if not f:
        return jsonify(error="No file uploaded."), 400
    try:
        return jsonify(linkedin.parse_upload(f.filename, f.read()))
    except ValueError as ex:
        return jsonify(error=str(ex)), 400


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
    if photo is None and payload.get("photo_url"):
        photo = linkedin.fetch_photo(str(payload["photo_url"]))

    buf = build_resume(payload, photo)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", payload["name"].strip()).strip("_") or "Resume"
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{safe}_Resume.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


