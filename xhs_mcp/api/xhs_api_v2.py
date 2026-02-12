import asyncio
import json
import time
from collections.abc import Mapping
from urllib.parse import urlencode
import requests
from curl_cffi.requests import AsyncSession, Response
import hashlib

from typing import Dict
import os
import execjs
from numbers import Integral
from typing import Iterable, List, Optional, Tuple
import random
import base64
from playwright.async_api import async_playwright

class XhsApiV2:
    def __init__(self,cookie):
        self._cookie=cookie
        self._base_url="https://edith.xiaohongshu.com"
        self._headers = {
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        self._playwright = None
        self._browser = None
        self._page = None

    async def start(self):
        """异步初始化 Playwright"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            # https://www.xiaohongshu.com/explore
            self._page = await self._browser.new_page()
            await self._page.goto("https://www.xiaohongshu.com/explore")
            
            # 预加载 JS 文件
            current_directory = os.path.dirname(__file__)
            file_path = os.path.join(current_directory, "xhsvm_v2.js")
            with open(file_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            await self._page.add_script_tag(content=js_content)

    async def close(self):
        """清理资源"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def init_session(self):
        return AsyncSession(
            verify=True,
            impersonate="chrome124"
        )

    def _parse_cookie(self, cookie: str) -> Dict:

        cookie_dict = {}
        if cookie:
            pairs = cookie.split(';')
            for pair in pairs:
                key, value = pair.strip().split('=', 1)
                cookie_dict[key] = value
        return cookie_dict



    async def request(self,uri: str,session=None, method="GET",headers=None,params=None,data=None) -> Dict:
        if session is None:
            session=self.init_session()
        if headers is None:
            headers = {}
        headers["x-s-common"]='2UQAPsHCPUIjqArjwjHjNsQhPsHCH0rjNsQhPaHCH0c1PUhlHjIj2eHjwjQ+GnPW/MPjNsQhPUHCHdYiqUMIGUM78nHjNsQh+sHCH0L1P/r1PsHVHdWMH0ijP/D7PemSw/Wl+AYEy0HUyo+72dP9GAPl40+MPgk18BkdyoWIq9bYJfrAPeZIPeHAP0ZAPsHVHdW9H0ijHjIj2eqjwjHjNsQhwsHCHDDAwoQH8B4AyfRI8FS98g+Dpd4daLP3JFSb/BMsn0pSPM87nrldzSzQ2bPAGdb7zgQB8nph8emSy9E0cgk+zSS1qgzianYt8LcE/LzN4gzaa/+NqMS6qS4HLozoqfQnPbZEp98QyaRSp9P98pSl4oSzcgmca/P78nTTL08z/sVManD9q9z1J9p/8db8aob7JeQl4epsPrz6agW3tF4ryaRApdz3agYDq7YM47HFqgzkanYMGLSbP9LA/bGIa/+nprSe+9LI4gzVPDbrJg+P4fprLFTALMm7+LSb4d+kpdzt/7b7wrQM498cqBzSpr8g/FSh+bzQygL9nSm7qSmM4epQ4flY/BQdqA+l4oYQ2BpAPp87arS34nMQyFSE8nkdqMD6pMzd8/4SL7bF8aRr+7+rG7mkqBpD8pSUzozQcA8Szb87PDSb/d+/qgzVJfl/4LExpdzQ4fRSy7bFP9+y+7+nJAzdaLp/2LSizgbzJFlpagYTLrRCJnRQyn+G8pm7zDS9yLPUc04Azoi7q7Yn4BzQ408S8eq78pSxLD4QznzS+S4jzozc49kQyrkAP9RSqA8r4fpLLozwGML98LzM4ApQ4SSdGFb68p+n4MQPwLRAzob7qDDA/nEQ2BMVq7bFq9bc47SAqFYjnDb98/+IN9prLo4haL+Sq9TrPBp/8LYkanD7q9kjJ7PA87QBanSD8/8M4A+QygQ34opFJgzM4r8Q2BpSpbmFzDSiafpkpdzVanTd8/mc4bP3qg4c2Sm7pLS9yBTQ2B+U+B4HcaTQ/fpkLozxanYU4rSiJ7+xqgzc/omzGg4Ua7+D8f+DanYCNAQM4MkU4g4/aL+Dq9Tc4bP3/LTSPn+mq9S+JLlQyLbA2e4SqMzM4oS0Lo4laLPI8n8n4bpQyLESpo+MLrSea9p8JA+SpM87+LSha7Pl4g4MaDQg8FS3tApQ2epS2BMNqM8m/7+rcnpSySm7nDSbpbzQc9+8qob7JLShyLbQy/mSpf+C8eQfP9px4g4oanSoGn+l4AZ3zrbSPnF7q9zl4BEPLoz1a/+BPFS9zgkTpdc3nS87qrDA/d+fGFRSpb874B+n4B4Q4dk7nSmFpLShz0YyPBD6anSdqM4dP7+gJURSpb878LYM4ozQyp4yagYOq9Tn4rpQzLTS8Sk3+LSizLT6npDUag8b2rSe+fp3qg4hqobFLjTc4b4QPF4eaLpmq9TmP9pnLoqAqrlQcFSez9z74gzz/bm7PDS9Le8Q2bbhaLp+/LS3ad+LJn4SPFl/8LkM474QPMPlGSmF4B+l4AmQyrTSzoQMqDSkp7bP8rbS2b8FGaTn4BRAJrclqdQknLSk/g8d4g4VanVIqA8gzB4QyMiRHjIj2eDjwjFl+ePl+0ZU+0H7NsQhP/Zjw0ZVHdWlPaHCHfE6qfMYJsHVHdWlPjHCH0r7+AZhw/GF+/D7PALvP/q9w/Z7+eZl+eLU+UQR'

        response: Response = await session.request(
            method=method,
            url=f"{self._base_url}{uri}",
            params=params,
            json=data,
            cookies=self._parse_cookie(self._cookie),
            quote=False,
            stream=True,
            headers=headers
        )


        content = await response.acontent()
        return json.loads(content)
    def base36encode(self,number: Integral, alphabet: Iterable[str] = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') -> str:

        base36 = ''
        alphabet = ''.join(alphabet)
        sign = '-' if number < 0 else ''
        number = abs(number)

        while number:
            number, i = divmod(number, len(alphabet))
            base36 = alphabet[i] + base36

        return sign + (base36 or alphabet[0])

    def search_id(self):
        e = int(time.time() * 1000) << 64
        t = int(random.uniform(0, 2147483646))
        return self.base36encode((e + t))

    async def get_xs_xt(self, data,md5, cookie):
        # 使用已初始化的 page 执行 JS 代码
        x_s = await self._page.evaluate("([data, md5, cookie]) => GetXs(data, md5, cookie)", [data, md5, cookie])
        x_t=int(time.time()*1000)
        print(x_s,x_t)
        return {"X-s":x_s,"X-t":x_t}
    async def get_me(self) -> Dict:
        uri = '/api/sns/web/v2/user/me'
        return await self.request(uri,method="GET")

    async def search_notes(self, keywords: str, limit: int = 20) -> Dict:
        data={
            "keyword":keywords,
            "page":1,
            "page_size":limit,
            "search_id":self.search_id(),
            "sort":"general",
            "note_type":0,
            "ext_flags":[],
            "geo":"",
            "image_formats":["jpg","webp","avif"]
        }
        headers = {
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        uri="/api/sns/web/v1/search/notes"
        uri_data=uri+json.dumps(data, separators=(",", ":"))
        # aa='/api/sns/web/v1/homefeed{"cursor_score":"1.7708818569900007E9","num":18,"refresh_type":3,"note_index":20,"unread_begin_note_id":"","unread_end_note_id":"","unread_note_count":0,"category":"homefeed.fashion_v3","search_key":"","need_num":8,"image_formats":["jpg","webp","avif"],"need_filter_image":false}'
        md5=hashlib.md5(uri_data.encode('utf-8')).hexdigest()
        xsxt=await self.get_xs_xt(uri_data,md5,self._cookie)
        headers['x-s']=xsxt['X-s']
        headers['x-t']=str(xsxt['X-t'])
        return await self.request(uri,method="POST",data=data,headers=headers)

    async def home_feed(self) -> Dict:

        data={
            "cursor_score":"",
            "num":18,
            "refresh_type":1,
            "note_index":10,
            "unread_begin_note_id":"",
            "unread_end_note_id":"",
            "unread_note_count":0,
            "category":"homefeed.fashion_v3",
            "search_key":"",
            "need_num":8,
            "image_formats":["jpg","webp","avif"],
            "need_filter_image":False
        }
        uri="/api/sns/web/v1/homefeed"
        p={"uri":uri,"method":"POST","data":data}
        headers = {
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        uri_data=uri+json.dumps(data, separators=(",", ":"))
        md5=hashlib.md5(uri_data.encode('utf-8')).hexdigest()
        xsxt=await self.get_xs_xt(uri_data,md5,self._cookie)
        headers['x-s']=xsxt['X-s']
        headers['x-t']=str(xsxt['X-t'])
        
        return await self.request(**p,headers=headers)


    async def get_note_content(self, note_id: str, xsec_token: str) -> Dict:
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg","webp","avif"],
            "extra": {"need_body_topic":"1"},
            "xsec_source": "pc_feed",
            "xsec_token": xsec_token
        }
        uri="/api/sns/web/v1/feed"
        p={"uri":uri,"method":"POST","data":data}
        headers = {
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        uri_data=uri+json.dumps(data, separators=(",", ":"))
        md5=hashlib.md5(uri_data.encode('utf-8')).hexdigest()
        xsxt=await self.get_xs_xt(uri_data,md5,self._cookie)
        headers['x-s']=xsxt['X-s']
        headers['x-t']=str(xsxt['X-t'])
        # 1762840901273
        # 1762841685584
        # headers['x-s-common']='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'

        return await self.request(**p,headers=headers)

    async def get_note_comments(self,note_id:str,xsec_token:str) -> Dict:
        uri = '/api/sns/web/v2/comment/page'
        # 680a25a4000000001c02d251
        # ABzm9YfVyNA1hsY-KwU7ybKNWlkpb8__t-jF9FwGKzZz0=
        params = {
            'note_id': note_id,
            'cursor': '',
            'top_comment_id': '',
            'image_formats': 'jpg,webp,avif',
            'xsec_token': xsec_token
        }


        return await self.request(uri,method="GET",params=params)

    async def post_comment(self,note_id:str, comment: str) -> Dict:
        uri='/api/sns/web/v1/comment/post'
        # 680ce9d1000000001c02cb9f
        data={
            "note_id":note_id,
            "content":comment,
            "at_users":[]
        }
        headers = {
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        uri_data=uri+json.dumps(data, separators=(",", ":"))
        md5=hashlib.md5(uri_data.encode('utf-8')).hexdigest()
        xsxt=await self.get_xs_xt(uri_data,md5,self._cookie)
        headers['x-s']=xsxt['X-s']
        headers['x-t']=str(xsxt['X-t'])
        return await self.request(uri, method="POST",headers=headers, data=data)

if __name__ == '__main__':
    async def main():
        xhs_api = XhsApiV2(cookie='')
        await xhs_api.start()
        try:
            aa = await xhs_api.get_note_comments("6986b48d000000001503aadf","ABMks7h8tzFAdpjE6bFcO4QdxkLRgECEyE7ry4QG7v7Y0=")
            print(aa)
        finally:
            await xhs_api.close()

    asyncio.run(main())
