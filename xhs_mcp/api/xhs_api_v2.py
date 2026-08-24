import asyncio
import json
import logging
import os
import random
import time
from numbers import Integral
from typing import Dict, Iterable, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_CAPTURE_XS_COMMON_JS = """
(() => {
  try {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  } catch (e) {}
  const store = (key, value) => {
    if (key && String(key).toLowerCase() === 'x-s-common' && value) {
      window.__xhs_xs_common = value;
    }
  };
  const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.setRequestHeader = function(key, value) {
    store(key, value);
    return origSetHeader.apply(this, arguments);
  };
  const origFetch = window.fetch;
  window.fetch = function(input, init) {
    try {
      const headers = init && init.headers;
      if (headers) {
        if (typeof Headers !== 'undefined' && headers instanceof Headers) {
          store('x-s-common', headers.get('X-S-Common') || headers.get('x-s-common'));
        } else if (Array.isArray(headers)) {
          for (const [key, value] of headers) store(key, value);
        } else if (typeof headers === 'object') {
          for (const [key, value] of Object.entries(headers)) store(key, value);
        }
      }
    } catch (e) {}
    return origFetch.apply(this, arguments);
  };
  window.__xhs_orig_fetch = origFetch.bind(window);
})();
"""

_SIGNED_FETCH_JS = """
async ({ url, method, data }) => {
  if (typeof window._webmsxyw !== 'function') {
    throw new Error('_webmsxyw is not available');
  }
  const parsed = new URL(url);
  const signUrl = parsed.pathname + parsed.search;
  const signed = data == null ? window._webmsxyw(signUrl) : window._webmsxyw(signUrl, data);
  const headers = {
    'content-type': 'application/json;charset=UTF-8',
    'X-s': signed['X-s'] || signed['x-s'] || '',
    'X-t': String(signed['X-t'] || signed['x-t'] || Date.now()),
  };
  if (window.__xhs_xs_common) {
    headers['X-S-Common'] = window.__xhs_xs_common;
  }
  const doFetch = window.__xhs_orig_fetch || fetch;
  const resp = await doFetch(url, {
    method,
    credentials: 'include',
    headers,
    body: data == null ? undefined : JSON.stringify(data),
  });
  const text = await resp.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    body = { success: false, msg: text.slice(0, 300), code: -1 };
  }
  return {
    status: resp.status,
    xsPrefix: String(headers['X-s']).slice(0, 8),
    body,
  };
}
"""


class XhsApiV2:
    def __init__(self, cookie):
        self._cookie = cookie
        self._base_url = "https://edith.xiaohongshu.com"
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._xs_common = None
        self._lock = asyncio.Lock()
        self._external_browser = False

    def _parse_cookie(self, cookie: str) -> Dict:
        cookie_dict = {}
        if cookie:
            for pair in cookie.split(";"):
                pair = pair.strip()
                if not pair or "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                # Cookie strings copied through Markdown/chat may escape
                # underscores (for example ``web\_session``). Browsers do not
                # include that backslash in the actual cookie name.
                cookie_dict[key.strip().replace("\\_", "_")] = value.strip()
        return cookie_dict

    def _playwright_cookies(self):
        cookies = []
        for name, value in self._parse_cookie(self._cookie).items():
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".xiaohongshu.com",
                "path": "/",
                "secure": True,
            })
        return cookies

    async def _apply_user_cookies(self):
        cookies = self._playwright_cookies()
        if not cookies or self._context is None:
            return
        await self._context.add_cookies(cookies)
        if self._page is not None and "xiaohongshu.com" in (self._page.url or ""):
            await self._page.evaluate(
                """(pairs) => {
                  for (const {name, value} of pairs) {
                    document.cookie = name + '=' + value + '; path=/; domain=.xiaohongshu.com; secure';
                  }
                }""",
                [{"name": item["name"], "value": item["value"]} for item in cookies],
            )

    async def start(self):
        """异步初始化 Playwright，并在官网页面里使用当前的签名函数。"""
        if self._playwright is not None:
            return
        self._playwright = await async_playwright().start()
        cdp_url = os.getenv("XHS_CDP_URL")
        launch_kwargs = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"],
            "ignore_default_args": ["--enable-automation"],
        }
        if cdp_url:
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
            self._external_browser = True
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            await self._page.add_init_script(_CAPTURE_XS_COMMON_JS)
            if self._page.url == "about:blank":
                await self._page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
            else:
                # An init script only runs for future documents. Reload the
                # dedicated CDP page once so signing headers are captured from
                # the page's own startup requests.
                await self._page.reload(wait_until="domcontentloaded")
        else:
            try:
                self._browser = await self._playwright.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception as e:
                logger.warning("system chrome unavailable (%s), falling back to bundled chromium", e)
                try:
                    self._browser = await self._playwright.chromium.launch(**launch_kwargs)
                except Exception:
                    self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            self._page = await self._context.new_page()
            await self._page.add_init_script(_CAPTURE_XS_COMMON_JS)
            if self._cookie:
                await self._apply_user_cookies()
            await self._page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")

        def _capture_common(request):
            try:
                value = request.headers.get("x-s-common") or request.headers.get("X-S-Common")
                if value:
                    self._xs_common = value
            except Exception:
                pass

        self._page.on("request", _capture_common)
        await self._page.wait_for_function(
            "() => typeof window._webmsxyw === 'function'",
            timeout=30000,
        )
        try:
            await self._page.wait_for_function(
                "() => !!window.__xhs_xs_common",
                timeout=8000,
            )
        except Exception:
            logger.warning("x-s-common was not captured during page load")
        logger.info("xiaohongshu sign runtime ready")

    async def close(self):
        """清理资源"""
        if self._external_browser:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
            return
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    def _build_url(self, uri: str, params: Optional[Dict] = None) -> str:
        url = f"{self._base_url}{uri}"
        if params:
            query = "&".join(
                f"{key}={'' if value is None else value}" for key, value in params.items()
            )
            url = f"{url}?{query}"
        return url

    async def request(self, uri: str, method="GET", params=None, data=None) -> Dict:
        if self._page is None:
            raise RuntimeError("XhsApiV2.start() must be called before requests")
        url = self._build_url(uri, params)
        async with self._lock:
            try:
                result = await self._page.evaluate(
                    _SIGNED_FETCH_JS,
                    {"url": url, "method": method, "data": data},
                )
            except Exception as e:
                logger.exception("xhs request failed: %s %s", method, uri)
                return {"success": False, "msg": str(e), "code": -1}
        logger.info(
            "xhs %s %s status=%s xs=%s",
            method,
            uri,
            result.get("status"),
            result.get("xsPrefix"),
        )
        body = result.get("body")
        return body if isinstance(body, dict) else {"success": False, "msg": "invalid response"}

    def base36encode(
        self,
        number: Integral,
        alphabet: Iterable[str] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    ) -> str:
        base36 = ""
        alphabet = "".join(alphabet)
        sign = "-" if number < 0 else ""
        number = abs(number)
        while number:
            number, i = divmod(number, len(alphabet))
            base36 = alphabet[i] + base36
        return sign + (base36 or alphabet[0])

    def search_id(self):
        e = int(time.time() * 1000) << 64
        t = int(random.uniform(0, 2147483646))
        return self.base36encode((e + t))

    async def get_me(self) -> Dict:
        return await self.request("/api/sns/web/v2/user/me", method="GET")

    async def search_notes(self, keywords: str, limit: int = 20) -> Dict:
        data = {
            "keyword": keywords,
            "page": 1,
            "page_size": limit,
            "search_id": self.search_id(),
            "sort": "general",
            "note_type": 0,
            "ext_flags": [],
            "geo": "",
            "image_formats": ["jpg", "webp", "avif"],
        }
        return await self.request("/api/sns/web/v1/search/notes", method="POST", data=data)

    async def home_feed(self) -> Dict:
        data = {
            "cursor_score": "",
            "num": 18,
            "refresh_type": 1,
            "note_index": 10,
            "unread_begin_note_id": "",
            "unread_end_note_id": "",
            "unread_note_count": 0,
            "category": "homefeed.fashion_v3",
            "search_key": "",
            "need_num": 8,
            "image_formats": ["jpg", "webp", "avif"],
            "need_filter_image": False,
        }
        return await self.request("/api/sns/web/v1/homefeed", method="POST", data=data)

    async def get_note_content(self, note_id: str, xsec_token: str) -> Dict:
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": "1"},
            "xsec_source": "pc_feed",
            "xsec_token": xsec_token,
        }
        return await self.request("/api/sns/web/v1/feed", method="POST", data=data)

    async def get_note_comments(self, note_id: str, xsec_token: str) -> Dict:
        params = {
            "note_id": note_id,
            "cursor": "",
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
        }
        return await self.request("/api/sns/web/v2/comment/page", method="GET", params=params)

    async def post_comment(self, note_id: str, comment: str) -> Dict:
        data = {
            "note_id": note_id,
            "content": comment,
            "at_users": [],
        }
        return await self.request("/api/sns/web/v1/comment/post", method="POST", data=data)


if __name__ == "__main__":
    async def main():
        xhs_api = XhsApiV2(cookie="")
        await xhs_api.start()
        try:
            me = await xhs_api.get_me()
            print(json.dumps({
                "code": me.get("code"),
                "success": me.get("success"),
                "msg": me.get("msg"),
                "guest": (me.get("data") or {}).get("guest"),
            }, ensure_ascii=False))
        finally:
            await xhs_api.close()

    asyncio.run(main())
