"""Entry point: python run.py (serves the Flask API with WebSocket support)."""
import os
import sys
from pathlib import Path

# Ensure we're running from the project root or backend directory
current = Path.cwd()
backend_path = Path(__file__).parent
project_root = backend_path.parent

# Change to project root to ensure relative paths work correctly
if current != project_root and current != backend_path:
    os.chdir(project_root)
    print(f"Changed working directory to: {project_root}")

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    print(f"Starting Brainr server from: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Backend root: {backend_path}")
    print(f"Port: {Config.PORT}")
    print(f"Debug: {Config.FLASK_ENV == 'development'}")
    
    # SocketIO is already initialized in create_app()
    # We need to get the socketio instance and use it to run the app
    try:
        from flask_socketio import SocketIO
        # Try to retrieve socketio from app extensions if available
        if hasattr(app, 'socketio'):
            socketio = app.socketio
        else:
            # If not attached to app, create a new instance (shouldn't happen with proper setup)
            from app.socket_events import init_socketio
            socketio = init_socketio(app)
        
        print("✓ WebSocket (SocketIO) enabled - Real-time email and WhatsApp listening active")
        
        # Use SocketIO's server which supports WebSockets
        socketio.run(
            app,
            host="0.0.0.0",
            port=Config.PORT,
            debug=(Config.FLASK_ENV == "development"),
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        print(f"⚠ SocketIO error ({e}) - Using standard Flask server")
        print("⚠ Real-time WebSocket updates will not be available")
        app.run(host="0.0.0.0", port=Config.PORT, debug=(Config.FLASK_ENV == "development"))
