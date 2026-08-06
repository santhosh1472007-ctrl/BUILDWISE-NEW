import os

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 5000))

    print(f"Starting BuildWise on {host}:{port}")

    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )