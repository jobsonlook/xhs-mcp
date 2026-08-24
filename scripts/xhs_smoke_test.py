"""Staged, secret-safe smoke test for the Xiaohongshu session."""

import argparse
import asyncio
import os
import sys

from xhs_mcp.api.xhs_api_v2 import XhsApiV2


REQUIRED_COOKIES = {"a1", "webId", "web_session"}


def is_authenticated(result: dict) -> bool:
    user = result.get("data") or {}
    return (
        result.get("success") is True
        and bool(user.get("user_id"))
        and not user.get("guest")
    )


def check_cookie_shape(api: XhsApiV2) -> bool:
    parsed = api._parse_cookie(api._cookie)
    missing = sorted(REQUIRED_COOKIES - parsed.keys())
    escaped = sorted(name for name in parsed if "\\" in name)

    print(f"Cookie fields parsed: {len(parsed)}")
    print(f"Required fields present: {not missing}")
    if missing:
        print("Missing fields: " + ", ".join(missing))
    if escaped:
        print("Invalid escaped field names: " + ", ".join(escaped))
    return bool(parsed) and not missing and not escaped


async def run(stage: str) -> int:
    cookie = os.getenv("XHS_COOKIE", "").strip()
    cdp_url = os.getenv("XHS_CDP_URL", "").strip()
    if not cookie and not cdp_url:
        print("Set XHS_COOKIE or XHS_CDP_URL", file=sys.stderr)
        return 2

    api = XhsApiV2(cookie=cookie)
    if cookie:
        if not check_cookie_shape(api):
            return 2
    else:
        print("Cookie injection: disabled (using CDP browser session)")
    if stage == "parse":
        return 0

    try:
        await api.start()
        names = {item["name"] for item in await api._context.cookies()}
        print(f"Browser page ready: {api._page.url.startswith('https://www.xiaohongshu.com/')}")
        print(f"Browser has web_session: {'web_session' in names}")
        if stage == "browser":
            return 0 if "web_session" in names else 1

        result = await api.get_me()
        authenticated = is_authenticated(result)
        print(f"API success: {result.get('success') is True}")
        print(f"Authenticated user: {authenticated}")
        print(f"Guest flag: {(result.get('data') or {}).get('guest')}")
        print(f"User ID present: {bool((result.get('data') or {}).get('user_id'))}")
        print(f"Response code: {result.get('code')}")
        print(f"Response message: {result.get('msg', '')}")
        if stage == "stability" and authenticated:
            feed = await api.home_feed()
            items = ((feed.get("data") or {}).get("items") or [])
            print(f"Home feed success: {feed.get('success') is True}")
            print(f"Home feed items: {len(items)}")

            after = await api.get_me()
            still_authenticated = is_authenticated(after)
            print(f"Authenticated after API call: {still_authenticated}")
            return 0 if feed.get("success") is True and still_authenticated else 1
        return 0 if authenticated else 1
    finally:
        await api.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test Cookie parsing, browser injection, or one read-only API call."
    )
    parser.add_argument(
        "--stage",
        choices=("parse", "browser", "api", "stability"),
        default="parse",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.stage)))


if __name__ == "__main__":
    main()
