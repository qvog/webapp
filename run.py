"""Dev launcher: FastAPI backend + Vite frontend."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def main() -> None:
    print("🚀 [SYSTEM] Starting qScalp Terminal (dev)...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    print("🐍 Backend → http://0.0.0.0:8000")
    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=base_dir,
    )

    time.sleep(1)

    print("⚡ Frontend → http://127.0.0.1:3005 (Vite proxies /api → :8000)")
    frontend = subprocess.Popen([npm_cmd, "run", "dev"], cwd=frontend_dir)

    def shutdown(*_args) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None or frontend.poll() is not None:
                print("⚠️ One of the servers exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        for name, proc in (("Backend", backend), ("Frontend", frontend)):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                print(f"✅ {name} stopped.")
        print("🏁 Done.")


if __name__ == "__main__":
    main()
