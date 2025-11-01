#!/usr/bin/env python3
"""
Automate environment setup for this repo:
- Create a Python virtual environment and install project dependencies from models/requirements.txt
- Optionally warm up YOLO weights to avoid first-run latency
- Optionally install Node.js backend dependencies (backend/package.json)

Usage:
    # Default: Python venv + pip install (auto-detect requirements in models/requirements.txt)
    python setup_environment.py

    # With YOLO warmup and backend deps
    python setup_environment.py --warmup --with-node

    # Customizations
    python setup_environment.py --requirements models/requirements.txt --venv .venv --model yolov8n.pt
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

EXCLUDE_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache"}

def log(msg: str) -> None:
    print(f"[setup] {msg}")

def error(msg: str) -> None:
    print(f"[setup][error] {msg}", file=sys.stderr)

def run(cmd: List[str], env: Optional[dict] = None, cwd: Optional[Path] = None) -> None:
    subprocess.run(cmd, check=True, env=env, cwd=str(cwd) if cwd else None)

def venv_python_path(venv_dir: Path) -> Path:
    if platform.system().lower().startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"

def create_venv(venv_dir: Path, base_python: str) -> Path:
    if not venv_dir.exists():
        log(f"Creating virtual environment at {venv_dir}")
        run([base_python, "-m", "venv", str(venv_dir)])
    else:
        log(f"Using existing virtual environment at {venv_dir}")
    vpy = venv_python_path(venv_dir)
    if not vpy.exists():
        # In rare cases, ensurepip might be needed
        log("Ensuring pip is available in the virtual environment")
        run([base_python, "-m", "venv", str(venv_dir), "--upgrade-deps"])
    return venv_python_path(venv_dir)

def find_requirements(start: Path) -> Optional[Path]:
    # Prefer models/requirements.txt if present
    candidate = start / "models" / "requirements.txt"
    if candidate.is_file():
        return candidate

    # Direct requirements.txt at root
    root_req = start / "requirements.txt"
    if root_req.is_file():
        return root_req

    # Recursive search excluding common virtual env and VCS dirs
    for path in start.rglob("requirements.txt"):
        parts = set(p.name for p in path.parents)
        if EXCLUDE_DIRS.isdisjoint(parts):
            return path
    return None

def ensure_python_version(min_major: int = 3, min_minor: int = 10) -> None:
    if sys.version_info < (min_major, min_minor):
        error(f"Python {min_major}.{min_minor}+ is required. Detected {platform.python_version()}.")
        sys.exit(1)

def main() -> None:
    ensure_python_version()

    parser = argparse.ArgumentParser(description="Set up project environment and install dependencies.")
    parser.add_argument("--venv", type=Path, default=Path(".venv"), help="Virtual environment directory (default: .venv)")
    parser.add_argument("--python", default=sys.executable, help="Base Python executable to create the venv (default: current Python)")
    parser.add_argument("--requirements", type=Path, help="Path to requirements.txt (auto-detect if omitted)")
    parser.add_argument("--no-upgrade", action="store_true", help="Skip upgrading pip/setuptools/wheel")
    parser.add_argument("--with-node", action="store_true", help="Install Node.js backend dependencies if backend/package.json exists")
    parser.add_argument("--warmup", action="store_true", help="Warm up YOLO model to pre-download weights and JIT caches")
    parser.add_argument("--model", default="yolov8n.pt", help="Model name or path to warm up (default: yolov8n.pt)")
    parser.add_argument("--backend-dir", type=Path, default=Path("backend"), help="Backend directory containing package.json (default: backend)")
    args = parser.parse_args()

    project_root = Path.cwd()
    req_path = args.requirements if args.requirements else find_requirements(project_root)
    if not req_path or not req_path.is_file():
        error("Could not locate requirements.txt. Provide with --requirements.")
        sys.exit(2)

    log(f"Project root: {project_root}")
    log(f"Using requirements file: {req_path}")

    # Create venv and get its python
    venv_dir = args.venv.resolve()
    vpy = create_venv(venv_dir, args.python)

    # Prepare environment for pip to reduce noise
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PYTHONUTF8", "1")

    # Ensure pip present and updated
    try:
        if not args.no_upgrade:
            log("Upgrading pip, setuptools, and wheel in the virtual environment")
            run([str(vpy), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], env=env)
        else:
            log("Skipping upgrade of pip/setuptools/wheel as requested")
    except subprocess.CalledProcessError:
        error("Failed to upgrade pip/setuptools/wheel.")
        sys.exit(3)

    # Install requirements
    try:
        log("Installing project dependencies")
        run([str(vpy), "-m", "pip", "install", "-r", str(req_path)], env=env)
    except subprocess.CalledProcessError:
        error("Failed to install dependencies from requirements.txt.")
        sys.exit(4)

    # Optionally install Node.js backend deps
    if args.with_node:
        backend_dir = (project_root / args.backend_dir).resolve()
        pkg = backend_dir / "package.json"
        if pkg.is_file():
            try:
                # Check node/npm availability
                log("Detected backend/package.json. Checking Node.js...")
                try:
                    subprocess.run(["node", "-v"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(["npm", "-v"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    error("Node.js or npm not found. Install Node 18+ from https://nodejs.org/ and re-run with --with-node.")
                    raise

                # Prefer npm ci when lockfile present
                if (backend_dir / "package-lock.json").is_file():
                    log("Installing backend deps with 'npm ci'")
                    run(["npm", "ci"], cwd=backend_dir)
                else:
                    log("Installing backend deps with 'npm install'")
                    run(["npm", "install"], cwd=backend_dir)
                log("Backend dependencies installed")
            except subprocess.CalledProcessError:
                error("Failed to install backend Node.js dependencies.")
                # Non-fatal for Python environment setup
        else:
            log(f"--with-node specified, but {backend_dir}/package.json not found. Skipping Node setup.")

    # Optional YOLO warmup to pre-download weights and reduce first-run latency
    if args.warmup:
        try:
            log("Warming up YOLO model (this may take a few minutes on first run)...")
            # Run a small Python snippet inside the venv to ensure it uses installed libs
            warmup_code = (
                "from ultralytics import YOLO;\n"
                f"model = YOLO(r'{args.model}');\n"
                "import numpy as np; img = np.zeros((640,640,3), dtype=np.uint8);\n"
                "model.predict(img, imgsz=640, verbose=False, conf=0.25);\n"
                "print('YOLO warmup complete')\n"
            )
            run([str(vpy), "-c", warmup_code], env=env)
        except subprocess.CalledProcessError:
            error("YOLO warmup failed. You can skip with --no-warmup or try again later.")

    # Suggest interpreter path for editors
    interp_path = str(vpy)
    log("Environment setup complete.")
    log(f"Virtual environment: {venv_dir}")
    log(f"Interpreter: {interp_path}")

    # Optionally write a .venv path file for VS Code Python extension
    try:
        vscode_dir = project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        settings_path = vscode_dir / "settings.json"
        python_setting = {
            "python.defaultInterpreterPath": interp_path
        }
        # Merge if exists
        existing = {}
        if settings_path.is_file():
            import json
            with settings_path.open("r", encoding="utf-8") as f:
                try:
                    existing = json.load(f) or {}
                except Exception:
                    existing = {}
            existing.update(python_setting)
            with settings_path.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=4)
        else:
            import json
            with settings_path.open("w", encoding="utf-8") as f:
                json.dump(python_setting, f, indent=4)
        log(f"Wrote VS Code interpreter setting to {settings_path}")
    except Exception as e:
        # Non-fatal
        log(f"Skipping VS Code settings update: {e}")

    # Final guidance
    if platform.system().lower().startswith("win"):
        # PowerShell activation script
        activate_hint = f".\\{venv_dir.name}\\Scripts\\Activate.ps1"
    else:
        activate_hint = f"source {venv_dir}/bin/activate"
    log(f"Activate the environment with: {activate_hint}")

if __name__ == "__main__":
    main()