"""
Video Auto Annotation - Web Application Launcher
One-click startup script for the web application.
"""
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "web" / "frontend"
BACKEND_MODULE = "web.backend.app:app"


def check_dependencies():
    missing = []
    for pkg in ["fastapi", "uvicorn", "sqlalchemy", "naive_ui_is_frontend_only"]:
        pass

    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")

    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")

    try:
        import sqlalchemy
    except ImportError:
        missing.append("sqlalchemy")

    try:
        import multipart
    except ImportError:
        missing.append("python-multipart")

    if missing:
        print(f"[ERROR] Missing Python packages: {', '.join(missing)}")
        print(f"        Run: pip install {' '.join(missing)}")
        return False
    return True


def check_frontend_dist():
    dist_dir = FRONTEND_DIR / "dist"
    index_html = dist_dir / "index.html"
    if not index_html.exists():
        print("[WARN] Frontend dist not found. Building frontend...")
        return build_frontend()
    print(f"[OK] Frontend dist found at {dist_dir}")
    return True


def build_frontend():
    npm_cmd = "npm"
    if sys.platform == "win32":
        npm_cmd = "npm.cmd"

    if not (FRONTEND_DIR / "node_modules").exists():
        print("[INFO] Installing frontend dependencies...")
        try:
            subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR), check=True)
        except FileNotFoundError:
            print("[ERROR] npm not found. Please install Node.js from https://nodejs.org/")
            return False
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to install frontend dependencies")
            return False

    print("[INFO] Building frontend...")
    try:
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), check=True)
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to build frontend")
        return False

    print("[OK] Frontend built successfully")
    return True


def start_server(host="0.0.0.0", port=8000, reload=False):
    print(f"\n{'='*50}")
    print(f"  Video Auto Annotation - Web Application")
    print(f"  Server: http://{host}:{port}")
    print(f"  API Docs: http://{host}:{port}/docs")
    print(f"{'='*50}\n")

    import uvicorn
    uvicorn.run(
        BACKEND_MODULE,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    print("=" * 50)
    print("  Video Auto Annotation - Startup Check")
    print("=" * 50 + "\n")

    if not check_dependencies():
        sys.exit(1)

    if not check_frontend_dist():
        print("[WARN] Frontend not available, running in API-only mode")
        print("       The web UI will not be accessible.")
        proceed = input("Continue anyway? (y/N): ").strip().lower()
        if proceed != "y":
            sys.exit(1)

    host = os.environ.get("VA_HOST", "0.0.0.0")
    port = int(os.environ.get("VA_PORT", "8000"))
    reload = os.environ.get("VA_RELOAD", "0") == "1"

    start_server(host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
