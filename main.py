# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""Windows desktop launcher: runs the Flask backend on a free local port
inside a native WebView2 window.

Author: Ishan Chakraborty
License: MIT
"""
import socket
import threading

import webview
from werkzeug.serving import make_server

from app import app

APP_TITLE = "Dynamic Resume Builder"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    port = _free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Allow the blob-based .docx download to show a Save dialog.
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window(APP_TITLE, f"http://127.0.0.1:{port}/", width=1200, height=850, min_size=(900, 600))
    webview.start()
    server.shutdown()


if __name__ == "__main__":
    main()

