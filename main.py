# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""Windows desktop launcher: runs the Flask backend on a free local port
inside a native WebView2 window.

Author: Ishan Chakraborty
License: MIT
"""
import os
import socket
import threading

import webview
from werkzeug.serving import make_server

from app import app

APP_TITLE = "Dynamic Resume Builder"


PREFERRED_PORT = 5000  # matches the default LinkedIn OAuth redirect URL


def _pick_port():
    """Use port 5000 (so the LinkedIn redirect URL is stable); fall back to any free port."""
    for candidate in (PREFERRED_PORT, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return s.getsockname()[1]
    raise RuntimeError("No free local port available")


def main():
    port = _pick_port()
    # Keep the OAuth redirect URL in sync with the port actually in use
    # (an explicit LINKEDIN_REDIRECT_URI from the user still wins).
    os.environ.setdefault("LINKEDIN_REDIRECT_URI", f"http://127.0.0.1:{port}/auth/linkedin/callback")
    server = make_server("127.0.0.1", port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Allow the blob-based .docx download to show a Save dialog.
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window(APP_TITLE, f"http://127.0.0.1:{port}/", width=1200, height=850, min_size=(900, 600))
    webview.start()
    server.shutdown()


if __name__ == "__main__":
    main()

