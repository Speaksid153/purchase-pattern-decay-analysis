"""Start the API and Nginx as one failure-coupled portfolio service."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from prepare_serving_cache import prepare_serving_cache


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "deployment" / "nginx.portfolio.conf.template"
GENERATED_CONFIG = Path("/tmp/nginx.portfolio.conf")


def _port(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        port = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if not 1024 <= port <= 65535:
        raise ValueError(f"{name} must be between 1024 and 65535")
    return port


def _stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 8
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    prepare_serving_cache()
    public_port = _port("PORT", 10000)
    api_port = _port("API_PORT", 5001)
    if public_port == api_port:
        raise ValueError("PORT and API_PORT must be different")

    config = TEMPLATE_PATH.read_text(encoding="utf-8")
    config = config.replace("${PORT}", str(public_port)).replace("${API_PORT}", str(api_port))
    GENERATED_CONFIG.write_text(config, encoding="utf-8")

    api_environment = os.environ.copy()
    api_environment.update({"API_HOST": "127.0.0.1", "API_PORT": str(api_port)})
    processes: list[subprocess.Popen[bytes]] = []
    stopping = False

    def handle_signal(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        api_process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "api_server.py")], env=api_environment
        )
        processes.append(api_process)
        readiness_deadline = time.monotonic() + 30
        health_url = f"http://127.0.0.1:{api_port}/api/health"
        while time.monotonic() < readiness_deadline and not stopping:
            if api_process.poll() is not None:
                print(f"API exited during startup with status {api_process.returncode}", flush=True)
                return api_process.returncode or 1
            try:
                with urllib.request.urlopen(health_url, timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            if stopping:
                return 0
            print("API did not become ready within 30 seconds", flush=True)
            return 1

        nginx_process = subprocess.Popen(
            ["nginx", "-c", str(GENERATED_CONFIG), "-g", "daemon off;"]
        )
        processes.append(nginx_process)
        while not stopping:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    print(f"A service process exited unexpectedly with status {return_code}", flush=True)
                    return return_code or 1
            time.sleep(0.25)
        return 0
    finally:
        _stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
