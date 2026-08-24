"""Start the persistent Xiaohongshu Chrome when needed, then run the MCP."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROFILE = ROOT / ".xhs-chrome-profile"
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
CDP_URL = f"http://{CDP_HOST}:{CDP_PORT}"


def cdp_is_ready() -> bool:
    try:
        with socket.create_connection((CDP_HOST, CDP_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def ensure_chrome() -> None:
    if cdp_is_ready():
        return
    if not CHROME.exists():
        raise RuntimeError(f"Google Chrome not found: {CHROME}")

    PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            str(CHROME),
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={PROFILE}",
            "https://www.xiaohongshu.com/explore",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(40):
        if cdp_is_ready():
            return
        time.sleep(0.25)
    raise RuntimeError("Chrome started but CDP port 9222 did not become ready")


def main() -> None:
    ensure_chrome()
    env = os.environ.copy()
    env["XHS_CDP_URL"] = CDP_URL
    env.pop("XHS_COOKIE", None)
    os.execvpe(
        sys.executable,
        [sys.executable, "-m", "xhs_mcp", *sys.argv[1:]],
        env,
    )


if __name__ == "__main__":
    main()
