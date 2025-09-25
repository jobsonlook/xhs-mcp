from typing import Any, List, Dict, Optional
import asyncio
import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP, Context

import requests
from .api.xhs_api import XhsApi
import logging
from urllib.parse import urlparse, parse_qs
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument("--type", type=str, default='stdio')
parser.add_argument("--port", type=int, default=8809)

args = parser.parse_args()

mcp = FastMCP("小红书", port=args.port)

xhs_cookie = os.getenv('XHS_COOKIE')

xhs_api = XhsApi(cookie=xhs_cookie)


def get_nodeid_token(url=None, note_ids=None):
    if note_ids is not None:
        note_id = note_ids[0,24]
        xsec_token = note_ids[24:]
        return {"note_id": note_id, "xsec_token": xsec_token}
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    note_id = parsed_url.path.split('/')[-1]
    xsec_token = None
    xsec_token_list = query_params.get('xsec_token', [None])
    if len(xsec_token_list) > 0:
        xsec_token = xsec_token_list[0]
    return {"note_id": note_id, "xsec_token": xsec_token}


@mcp.tool()
async def check_cookie() -> str:
    """检测cookie是否失效

    """
    try:
        data = await xhs_api.get_me()

        if 'success' in data and data['success'] == True:
            return "cookie有效"
        else:
            return "cookie已失效"
    except Exception as e:
        logger.error(e)
        return "cookie已失效"



@mcp.tool()
async def home_feed() -> str:
    """获取首页推荐笔记

    """
    data = await xhs_api.home_feed()
    result = "搜索结果：\n\n"
    if 'data' in data and 'items' in data['data'] and len(data['data']['items']) > 0:
        for i in range(0, len(data['data']['items'])):
            item = data['data']['items'][i]
            if 'note_card' in item and 'display_title' in item['note_card']:
                title = item['note_card']['display_title']
                liked_count = item['note_card']['interact_info']['liked_count']
                # cover=item['note_card']['cover']['url_default']
                url = f'https://www.xiaohongshu.com/explore/{item["id"]}?xsec_token={item["xsec_token"]}'
                result += f"{i}. {title}  \n 点赞数:{liked_count} \n   链接: {url}  \n\n"
    else:
        result = await check_cookie()
        if "有效" in result:
            result = f"未找到相关的笔记"
    return result

@mcp.tool()
async def search_notes(keywords: str) -> str:
    """根据关键词搜索笔记

        Args:
            keywords: 搜索关键词
    """

    data = await xhs_api.search_notes(keywords)
    logger.info(f'keywords:{keywords},data:{data}')
    result = "搜索结果：\n\n"
    if 'data' in data and 'items' in data['data'] and len(data['data']['items']) > 0:
        for i in range(0, len(data['data']['items'])):
            item = data['data']['items'][i]
            if 'note_card' in item and 'display_title' in item['note_card']:
                title = item['note_card']['display_title']
                liked_count = item['note_card']['interact_info']['liked_count']
                # cover=item['note_card']['cover']['url_default']
                url = f'https://www.xiaohongshu.com/explore/{item["id"]}?xsec_token={item["xsec_token"]}'
                result += f"{i}. {title}  \n 点赞数:{liked_count} \n   链接: {url}  \n\n"
    else:
        result = await check_cookie()
        if "有效" in result:
            result = f"未找到与\"{keywords}\"相关的笔记"
    return result


@mcp.tool()
async def get_note_content(url: str) -> str:
    """获取笔记内容,参数url要带上xsec_token

    Args:
        url: 笔记 url
    """
    params = get_nodeid_token(url=url)
    data = await xhs_api.get_note_content(**params)
    logger.info(f'url:{url},data:{data}')
    result = ""
    if 'data' in data and 'items' in data['data'] and len(data['data']['items']) > 0:
        for i in range(0, len(data['data']['items'])):
            item = data['data']['items'][i]

            if 'note_card' in item and 'user' in item['note_card']:
                note_card = item['note_card']
                cover = ''
                if 'image_list' in note_card and len(note_card['image_list']) > 0 and note_card['image_list'][0][
                    'url_pre']:
                    cover = note_card['image_list'][0]['url_pre']

                data_format = datetime.fromtimestamp(note_card.get('time', 0) / 1000)
                liked_count = item['note_card']['interact_info']['liked_count']
                comment_count = item['note_card']['interact_info']['comment_count']
                collected_count = item['note_card']['interact_info']['collected_count']

                url = f'https://www.xiaohongshu.com/explore/{params["note_id"]}?xsec_token={params["xsec_token"]}'
                result = f"标题: {note_card.get('title', '')}\n"
                result += f"作者: {note_card['user'].get('nickname', '')}\n"
                result += f"发布时间: {data_format}\n"
                result += f"点赞数: {liked_count}\n"
                result += f"评论数: {comment_count}\n"
                result += f"收藏数: {collected_count}\n"
                result += f"链接: {url}\n\n"
                result += f"内容:\n{note_card.get('desc', '')}\n"
                result += f"封面:\n{cover}"

            break
    else:
        result = await check_cookie()
        if "有效" in result:
            result = "获取失败"
    return result


@mcp.tool()
async def get_note_comments(url: str) -> str:
    """获取笔记评论,参数url要带上xsec_token

    Args:
        url: 笔记 url
    

    """
    params = get_nodeid_token(url=url)

    data = await xhs_api.get_note_comments(**params)
    logger.info(f'url:{url},data:{data}')

    result = ""
    if 'data' in data and 'comments' in data['data'] and len(data['data']['comments']) > 0:
        for i in range(0, len(data['data']['comments'])):
            item = data['data']['comments'][i]
            data_format = datetime.fromtimestamp(item['create_time'] / 1000)

            result += f"{i}. {item['user_info']['nickname']}（{data_format}）: {item['content']}\n\n"

    else:
        result = await check_cookie()
        if "有效" in result:
            result = "暂无评论"

    return result


@mcp.tool()
async def post_comment(comment: str, note_id: str) -> str:
    """发布评论到指定笔记

    Args:
        note_id: 笔记 note_id
        comment: 要发布的评论内容
    """
    # params = get_nodeid_token(url)
    response = await xhs_api.post_comment(note_id, comment)
    if 'success' in response and response['success'] == True:
        return "回复成功"
    else:
        result = await check_cookie()
        if "有效" in result:
            return "回复失败"
        else:
            return result


def main():
    """主入口函数，用于uvx调用"""
    logger.info("mcp run")
    mcp.run(transport=args.type)

if __name__ == "__main__":
    main()
