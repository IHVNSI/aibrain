"""Entry point: python run.py (serves the Flask API)."""
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
    print(f"Starting Flask server from: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Backend root: {backend_path}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=(Config.FLASK_ENV == "development"))
