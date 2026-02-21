"""Dev entry point: pywebview pointing at Vite dev server.

Usage:
    1. Start Vite:    cd frontend && npm run dev
    2. Start FastAPI:  uvicorn api:app --reload
    3. Open window:    python dev.py
"""

import webview


def main():
    window = webview.create_window(
        "Hybrid Inference (Dev)",
        url="http://127.0.0.1:5173",
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == "__main__":
    main()
