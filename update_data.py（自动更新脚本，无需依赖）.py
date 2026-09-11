#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖数据自动更新脚本
使用Python自带的urllib，无需安装第三方依赖
"""

import urllib.request
import urllib.parse
import json
import os
import time
import random

# 请求头，模拟浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.cwl.gov.cn/',
}

# 数据保存目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_url(url, timeout=15):
    """用urllib发送GET请求"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f'请求失败 {url}: {e}')
        return None


def fetch_cwl(name, count=100):
    """
    抓取福彩数据
    name: ssq(双色球), 3d(3D), kl8(快乐8)
    """
    url = f'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name={name}&issueCount={count}'
    text = fetch_url(url)
    if not text:
        return []
    try:
        data = json.loads(text)
        result = []
        for item in data.get('result', []):
            red_balls = []
            blue_balls = []
            if name == 'ssq':
                red_str = item.get('red', '')
                blue_str = item.get('blue', '')
                red_balls = [int(x) for x in red_str.split(',') if x.strip()]
                blue_balls = [int(x) for x in blue_str.split(',') if x.strip()]
            elif name == '3d':
                red_str = item.get('red', '')
                red_balls = [int(x) for x in red_str.split(',') if x.strip()]
            elif name == 'kl8':
                red_str = item.get('red', '')
                red_balls = [int(x) for x in red_str.split(',') if x.strip()]
            result.append({
                'issue': item.get('code', ''),
                'date': item.get('date', '')[:10] if item.get('date') else '',
                'week': item.get('week', ''),
                'red': red_balls,
                'blue': blue_balls,
                'sales': item.get('sales', ''),
                'poolmoney': item.get('poolmoney', ''),
            })
        return result
    except Exception as e:
        print(f'解析福彩{name}数据失败: {e}')
        return []


def fetch_sporttery(lottery_id, count=100):
    """
    抓取体彩数据
    lottery_id: 大乐透=dlt, 排列3=pl3, 排列5=pl5, 七星彩=qxc
    使用体彩官方API
    """
    # 体彩官方开奖API
    url_map = {
        'dlt': 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1',
        'pl3': 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=35&provinceId=0&pageSize=100&isVerify=1&pageNo=1',
        'pl5': 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=35&provinceId=0&pageSize=100&isVerify=1&pageNo=1',
        'qxc': 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=04&provinceId=0&pageSize=100&isVerify=1&pageNo=1',
    }
    url = url_map.get(lottery_id)
    if not url:
        return []
    text = fetch_url(url)
    if not text:
        return []
    try:
        data = json.loads(text)
        result = []
        list_data = data.get('value', {}).get('list', [])
        for item in list_data:
            draw_result = item.get('lotteryDrawResult', '')
            draw_time = item.get('lotteryDrawTime', '')
            issue = item.get('lotteryDrawNum', '')

            if lottery_id == 'dlt':
                # 大乐透: 前区5个 + 后区2个，格式如 "01 02 03 04 05 + 06 07"
                parts = draw_result.replace('+', ' ').split()
                parts = [p for p in parts if p.strip()]
                front = [int(x) for x in parts[:5]] if len(parts) >= 5 else []
                back = [int(x) for x in parts[5:7]] if len(parts) >= 7 else []
                result.append({
                    'issue': issue,
                    'date': draw_time,
                    'front': front,
                    'back': back,
                    'red': front,
                    'blue': back,
                })
            elif lottery_id in ('pl3', 'pl5'):
                # 排列3/5: 数字直接排列
                nums = [int(x) for x in draw_result.replace(' ', '') if x.isdigit()]
                result.append({
                    'issue': issue,
                    'date': draw_time,
                    'numbers': nums,
                    'red': nums,
                })
            elif lottery_id == 'qxc':
                # 七星彩: 7位数字
                nums = [int(x) for x in draw_result.replace(' ', '') if x.isdigit()]
                result.append({
                    'issue': issue,
                    'date': draw_time,
                    'numbers': nums,
                    'red': nums,
                })
        return result
    except Exception as e:
        print(f'解析体彩{lottery_id}数据失败: {e}')
        return []


def save_json(filename, data):
    """保存JSON文件"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已保存 {filename}: {len(data)} 条数据')


def main():
    print('=== 开始更新彩票开奖数据 ===')
    print(f'数据目录: {DATA_DIR}')

    # 福彩
    print('\n--- 抓取福利彩票 ---')
    ssq = fetch_cwl('ssq', 100)
    save_json('ssq.json', ssq)
    time.sleep(random.uniform(1, 2))

    d3 = fetch_cwl('3d', 100)
    save_json('3d.json', d3)
    time.sleep(random.uniform(1, 2))

    kl8 = fetch_cwl('kl8', 100)
    save_json('kl8.json', kl8)
    time.sleep(random.uniform(1, 2))

    # 体彩
    print('\n--- 抓取体育彩票 ---')
    dlt = fetch_sporttery('dlt', 100)
    save_json('dlt.json', dlt)
    time.sleep(random.uniform(1, 2))

    pl3 = fetch_sporttery('pl3', 100)
    save_json('pl3.json', pl3)
    time.sleep(random.uniform(1, 2))

    pl5 = fetch_sporttery('pl5', 100)
    save_json('pl5.json', pl5)
    time.sleep(random.uniform(1, 2))

    qxc = fetch_sporttery('qxc', 100)
    save_json('qxc.json', qxc)

    print('\n=== 数据更新完成 ===')
    print(f'双色球最新: {ssq[0]["issue"] if ssq else "无"} 期')
    print(f'大乐透最新: {dlt[0]["issue"] if dlt else "无"} 期')


if __name__ == '__main__':
    main()
#（注：内容由AI生成）
