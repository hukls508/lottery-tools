#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖数据自动抓取脚本
抓取双色球(ssq)、大乐透(dlt)、排列3(p3)、排列5(p5)、7星彩(qxc)
数据源：中国福彩官网API + 中国体彩官网API + 500彩票网
"""
import json
import os
import re
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

def fetch_html(url, retries=3, delay=2, extra_headers=None):
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  抓取失败(第{attempt+1}次): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None

# ===== 双色球 =====
def fetch_ssq():
    print("[双色球] 开始抓取...")
    url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=30"
    data = fetch_json(url)
    if not data or data.get("state") != 0:
        print("[双色球] API返回异常，跳过")
        return []
    results = []
    for item in data.get("result", []):
        issue = item.get("code", "")
        date = item.get("date", "").split("(")[0].strip()
        try:
            red = [int(x) for x in item.get("red", "").split(",")]
            blue = int(item.get("blue", ""))
        except (ValueError, AttributeError):
            continue
        if len(red) == 6 and all(1 <= n <= 33 for n in red) and 1 <= blue <= 16:
            results.append({"issue": issue, "date": date, "red": red, "blue": blue})
    print(f"[双色球] 获取到 {len(results)} 期数据")
    return results

# ===== 大乐透 =====
def fetch_dlt():
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
        try:
            nums = [int(x) for x in item.get("lotteryDrawResult", "").split()]
        except (ValueError, AttributeError):
            continue
        if len(nums) == 7:
            front, back = nums[:5], nums[5:]
            if all(1 <= n <= 35 for n in front) and all(1 <= n <= 12 for n in back):
                results.append({"issue": issue, "date": date, "front": front, "back": back})
    print(f"[大乐透] 获取到 {len(results)} 期数据")
    return results

# ===== 排列3/排列5（体彩API gameNo=35）=====
def fetch_pl35():
    print("[排列3/5] 开始抓取...")
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=35&provinceId=0&pageSize=35&isVerify=1&pageNo=1"
    data = fetch_json(url, extra_headers={"Referer": "https://www.lottery.gov.cn/"})
    if not data or not data.get("success"):
        print("[排列3/5] API返回异常，跳过")
        return [], []
    p3_results, p5_results = [], []
    for item in data.get("value", {}).get("list", []):
        issue = item.get("lotteryDrawNum", "")
        date = item.get("lotteryDrawTime", "")
        try:
            p3_nums = [int(x) for x in item.get("lotteryDrawResult", "").split()]
            p5_nums = [int(x) for x in item.get("lotteryUnsortDrawresult", "").split()]
        except (ValueError, AttributeError):
            continue
        if len(p3_nums) == 3 and all(0 <= n <= 9 for n in p3_nums):
            p3_results.append({"issue": issue, "date": date, "digits": p3_nums})
        if len(p5_nums) == 5 and all(0 <= n <= 9 for n in p5_nums):
            p5_results.append({"issue": issue, "date": date, "digits": p5_nums})
    print(f"[排列3] 获取到 {len(p3_results)} 期，[排列5] 获取到 {len(p5_results)} 期")
    return p3_results, p5_results

# ===== 7星彩（500彩票网，只抓最新一期）=====
def fetch_qxc():
    print("[7星彩] 开始抓取...")
    url = "https://kaijiang.500.com/qxc.shtml"
    html = fetch_html(url, extra_headers={
        "Referer": "https://www.500.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    if not html:
        print("[7星彩] 抓取失败，跳过")
        return []
    # 提取最新期号
    issue_m = re.search(r'>(\d{5})<', html)
    # 提取最新日期（页面GBK编码，日期为7位数字如2026825=2026-08-25）
    date = ""
    # 匹配7位：年份4位 + 月份1位 + 日期2位
    for m in re.finditer(r'(?<!\d)(20[2-3]\d)(\d)(\d{2})(?!\d)', html):
        y, mo, da = m.group(1), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 9 and 1 <= da <= 31:
            date = f"{y}-{m.group(2).zfill(2)}-{m.group(3)}"
            break
    # 匹配7位：年份4位 + 月份2位 + 日期1位
    if not date:
        for m in re.finditer(r'(?<!\d)(20[2-3]\d)(\d{2})(\d)(?!\d)', html):
            y, mo, da = m.group(1), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= da <= 9:
                date = f"{y}-{m.group(2)}-{m.group(3).zfill(2)}"
                break
    # 匹配8位：年份4位 + 月份2位 + 日期2位
    if not date:
        for m in re.finditer(r'(?<!\d)(20[2-3]\d)(\d{2})(\d{2})(?!\d)', html):
            y, mo, da = m.group(1), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= da <= 31:
                date = f"{y}-{m.group(2)}-{m.group(3)}"
                break
    # 提取最新7位号码
    balls = re.findall(r'ball_orange[^>]*>(\d+)<', html)
    if not balls:
        balls = re.findall(r'class="ball[^"]*"[^>]*>(\d+)<', html)
    if issue_m and date and len(balls) >= 7:
        issue = issue_m.group(1)
        try:
            digits = [int(x) for x in balls[:7]]
        except ValueError:
            print("[7星彩] 号码解析失败，跳过")
            return []
        if all(0 <= n <= 14 for n in digits):
            print(f"[7星彩] 获取到最新一期: {issue} {date} {digits}")
            return [{"issue": issue, "date": date, "digits": digits}]
    print("[7星彩] 解析失败，跳过")
    return []

# ===== 通用函数 =====
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

def update_lottery(name, fetch_func, filename):
    remote = fetch_func()
    if not remote:
        return False
    filepath = os.path.join(DATA_DIR, filename)
    local = load_json(filepath)
    merged, new_count = merge_data(local, remote)
    if new_count > 0:
        save_json(filepath, merged)
        print(f"[{name}] 新增 {new_count} 期，最新: {merged[0]['issue']} ({merged[0]['date']})")
        return True
    else:
        print(f"[{name}] 无新数据，当前最新: {local[0]['issue'] if local else '无'}")
        return False

def main():
    print("=" * 50)
    print("彩票开奖数据自动抓取")
    print(f"数据目录: {DATA_DIR}")
    print("=" * 50)
    updated = False
    # 双色球
    if update_lottery("双色球", fetch_ssq, "ssq.json"): updated = True
    print()
    # 大乐透
    if update_lottery("大乐透", fetch_dlt, "dlt.json"): updated = True
    print()
    # 排列3/排列5
    p3_data, p5_data = fetch_pl35()
    if p3_data:
        if update_lottery("排列3", lambda: p3_data, "p3.json"): updated = True
    if p5_data:
        if update_lottery("排列5", lambda: p5_data, "p5.json"): updated = True
    print()
    # 7星彩
    if update_lottery("7星彩", fetch_qxc, "qxc.json"): updated = True
    print()
    print("=" * 50)
    if updated:
        print("✓ 有数据更新，需要提交到仓库")
        print("::set-output name=updated::true")
    else:
        print("✓ 无新数据")
        print("::set-output name=updated::false")
    print("=" * 50)

if __name__ == "__main__":
    main()
