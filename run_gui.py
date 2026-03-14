"""Windows-friendly launcher for the PriceScout web interface.

This script is designed to be started by double-clicking on Windows.
It uses the local ``venv`` interpreter when available, ensures required
packages are installed, starts the PriceScout backend, waits for readiness,
and opens the browser to the single-page frontend.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from urllib import error as urllib_error
from urllib import request as urllib_request
import webbrowser

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
HEALTH_URL = f"{BASE_URL}/health"
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "requests",
    "beautifulsoup4",
    "sqlalchemy",
]


def _project_root() -> Path:
    """Return repository root (directory containing this launcher)."""
    return Path(__file__).resolve().parent


def _venv_python(project_root: Path) -> Path:
    """Return venv Python path when available, otherwise current interpreter."""
    candidate = project_root / "venv" / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def _run_command(python_exe: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Execute a Python command and return the completed process."""
    command = [str(python_exe), *args]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(_project_root()),
    )


def _ensure_pip(python_exe: Path) -> None:
    """Ensure pip is available for the selected interpreter."""
    result = _run_command(python_exe, ["-m", "pip", "--version"])
    if result.returncode == 0:
        return

    print("pip is missing for selected interpreter; bootstrapping with ensurepip...")
    ensurepip_result = _run_command(python_exe, ["-m", "ensurepip", "--upgrade"])
    if ensurepip_result.returncode != 0:
        raise RuntimeError(
            "Failed to initialize pip.\n"
            f"STDOUT: {ensurepip_result.stdout}\n"
            f"STDERR: {ensurepip_result.stderr}"
        )


def _missing_packages(python_exe: Path) -> list[str]:
    """Return required packages that are missing for the selected interpreter."""
    missing: list[str] = []
    for package in REQUIRED_PACKAGES:
        show_result = _run_command(python_exe, ["-m", "pip", "show", package])
        if show_result.returncode != 0:
            missing.append(package)
    return missing


def _install_missing_packages(python_exe: Path) -> None:
    """Install only missing dependencies with pip."""
    missing = _missing_packages(python_exe)
    if not missing:
        print("All required dependencies are already installed.")
        return

    print(f"Installing missing dependencies: {', '.join(missing)}")
    install_result = _run_command(
        python_exe,
        ["-m", "pip", "install", *missing],
    )
    if install_result.returncode != 0:
        raise RuntimeError(
            "Dependency installation failed.\n"
            f"STDOUT: {install_result.stdout}\n"
            f"STDERR: {install_result.stderr}"
        )


def _wait_for_backend(timeout_seconds: int = 30) -> bool:
    """Wait until backend health endpoint responds with HTTP 200."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib_request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib_error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    return False


def _start_backend(python_exe: Path, project_root: Path) -> subprocess.Popen[str]:
    """Start the backend process using the selected interpreter."""
    child_env = os.environ.copy()
    child_env["PRICESCOUT_HOST"] = HOST
    child_env["PRICESCOUT_PORT"] = str(PORT)

    return subprocess.Popen(
        [str(python_exe), "-m", "pricescout.app.main"],
        cwd=str(project_root),
        env=child_env,
        stdout=None,
        stderr=None,
        text=True,
    )


def main() -> None:
    """Run PriceScout backend and open the web UI."""
    project_root = _project_root()
    python_exe = _venv_python(project_root)

    print(f"Using Python interpreter: {python_exe}")
    _ensure_pip(python_exe)
    _install_missing_packages(python_exe)

    backend_process = _start_backend(python_exe, project_root)

    try:
        print(f"Starting PriceScout backend at {BASE_URL} ...")
        if not _wait_for_backend(timeout_seconds=30):
            raise RuntimeError("Backend did not become ready in time.")

        print(f"Opening browser at {BASE_URL}/")
        webbrowser.open(f"{BASE_URL}/")

        print("PriceScout is running. Press Ctrl+C in this window to stop.")
        backend_process.wait()
    except KeyboardInterrupt:
        print("Stopping PriceScout...")
    finally:
        if backend_process.poll() is None:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_process.kill()


if __name__ == "__main__":
    main()
