#!/usr/bin/env python3
"""
Convenience launcher for VIGIL (§11):
Launches both backend (Uvicorn on port 8000) and frontend (Vite on port 5173) in offline mode.
"""

import subprocess
import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent


def main():
    print("=" * 60)
    print("VIGIL v3.1 — Master Demo Launcher (Offline Mode)")
    print("=" * 60)

    # Ensure demo is seeded
    python_bin = root_dir / ".venv" / "Scripts" / "python.exe"
    if not python_bin.exists():
        python_bin = "python"

    print("Checking database seed data...")
    # Run from the repo root so the seed and the API share the same ./vigil.db
    subprocess.run([str(python_bin), str(root_dir / "scripts" / "seed_demo.py")], cwd=str(root_dir), check=False)

    print("\nStarting FastAPI backend server on http://localhost:8000...")
    backend_proc = subprocess.Popen(
        [str(python_bin), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(root_dir)
    )

    print("Starting Vite frontend development server on http://localhost:5173...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(root_dir / "frontend"),
        shell=True
    )

    print("\nServices are running:")
    print("  - Web UI: http://localhost:5173")
    print("  - API Docs: http://localhost:8000/docs")
    print("  - Health Endpoint: http://localhost:8000/api/v1/health")
    print("\nPress Ctrl+C to terminate both servers.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_proc.terminate()
        if sys.platform == "win32":
            # npm runs through a shell: terminate() would leave the Vite (node) child running.
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], check=False)
        else:
            frontend_proc.terminate()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
