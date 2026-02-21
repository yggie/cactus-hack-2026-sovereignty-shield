"""Production entry point: pywebview + uvicorn serving the built frontend."""

import threading
import time

import uvicorn
import webview


def start_server():
    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="info")


def main():
    # Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Give uvicorn a moment to bind
    time.sleep(1)

    # Open pywebview on the main thread (required by macOS/Cocoa)
    window = webview.create_window(
        "Hybrid Inference",
        url="http://127.0.0.1:8000",
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == "__main__":
    main()
