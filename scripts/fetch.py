#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖数据自动抓取脚本
抓取双色球(ssq)和大乐透(dlt)最新开奖数据，更新到 data/*.json
数据源：中国福彩官网API + 中国体彩官网API
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def fetch_json(url, retries=3, delay=2, extra_headers=None):
    """抓取JSON数据，带重试"""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  抓取失败(第{attempt+1}次): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None

def fetch_ssq():
    """抓取双色球数据（中国福彩官网API）"""
    print("[双色球] 开始抓取...")
    url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=30"
    data = fetch_json(url)
    if not data or data.get("state") != 0:
        print("[双色球] API返回异常，跳过")
        return []
    results = []
    for item in data.get("result", []):
        issue = item.get("code", "")
        date_raw = item.get("date", "")
        # 日期格式 "2026-08-25(二)" -> "2026-08-25"
        date = date_raw.split("(")[0].strip()
        red_str = item.get("red", "")
        blue_str = item.get("blue", "")
        try:
            red = [int(x) for x in red_str.split(",")]
            blue = int(blue_str)
        except (ValueError, AttributeError):
            continue
        if len(red) == 6 and all(1 <= n <= 33 for n in red) and 1 <= blue <= 16:
            results.append({"issue": issue, "date": date, "red": red, "blue": blue})
    print(f"[双色球] 获取到 {len(results)} 期数据")
    return results

def fetch_dlt():
    """抓取大乐透数据（中国体彩官网API）"""
    print("[大乐透] 开始抓取...")
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=30&isVerify=1&pageNo=1"
    data = fetch_json(url, extra_headers={"Referer": "https://www.lottery.gov.cn/"})
    if not data or not data.get("success"):
        print("[大乐透] API返回异常，跳过")
        return []
    results = []
    for item in data.get("value", {}).get("list", []):
        issue = item.get("lotteryDrawNum", "")
        date = item.get("lotteryDrawTime", "")
        result_str = item.get("lotteryDrawResult", "")
        try:
            nums = [int(x) for x in result_str.split()]
        except (ValueError, AttributeError):
            continue
        if len(nums) == 7:
            front = nums[:5]
            back = nums[5:]
            if all(1 <= n <= 35 for n in front) and all(1 <= n <= 12 for n in back):
                results.append({"issue": issue, "date": date, "front": front, "back": back})
    print(f"[大乐透] 获取到 {len(results)} 期数据")
    return results

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  读取 {filepath} 失败: {e}")
        return []

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge_data(local_data, remote_data, key="issue"):
    existing = {item[key] for item in local_data}
    new_items = [item for item in remote_data if item[key] not in existing]
    if not new_items:
        return local_data, 0
    merged = local_data + new_items
    merged.sort(key=lambda x: x[key], reverse=True)
    return merged, len(new_items)

def update_ssq():
    remote = fetch_ssq()
    if not remote:
        return False
    filepath = os.path.join(DATA_DIR, "ssq.json")
    local = load_json(filepath)
    merged, new_count = merge_data(local, remote)
    if new_count > 0:
        save_json(filepath, merged)
        print(f"[双色球] 新增 {new_count} 期，最新: {merged[0]['issue']} ({merged[0]['date']})")
        return True
    else:
        print(f"[双色球] 无新数据，当前最新: {local[0]['issue'] if local else '无'}")
        return False

def update_dlt():
    remote = fetch_dlt()
    if not remote:
        return False
    filepath = os.path.join(DATA_DIR, "dlt.json")
    local = load_json(filepath)
    merged, new_count = merge_data(local, remote)
    if new_count > 0:
        save_json(filepath, merged)
        print(f"[大乐透] 新增 {new_count} 期，最新: {merged[0]['issue']} ({merged[0]['date']})")
        return True
    else:
        print(f"[大乐透] 无新数据，当前最新: {local[0]['issue'] if local else '无'}")
        return False

def main():
    print("=" * 50)
    print("彩票开奖数据自动抓取")
    print(f"数据目录: {DATA_DIR}")
    print("=" * 50)
    ssq_updated = update_ssq()
    print()
    dlt_updated = update_dlt()
    print()
    print("=" * 50)
    if ssq_updated or dlt_updated:
        print("✓ 有数据更新，需要提交到仓库")
        print("::set-output name=updated::true")
    else:
        print("✓ 无新数据")
        print("::set-output name=updated::false")
    print("=" * 50)

if __name__ == "__main__":
    main()
