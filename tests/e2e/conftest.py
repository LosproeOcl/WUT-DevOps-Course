# -*- coding: utf-8 -*-
import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CARS_DB_PATH", str(tmp_path / "cars.db"))

    from app.main import app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()
