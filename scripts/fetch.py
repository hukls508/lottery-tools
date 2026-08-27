
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票开奖数据自动抓取脚本
统一从500彩票网抓取HTML页面解析
支持：双色球(ssq)、大乐透(dlt)、排列3(p3)、排列5(p5)、7星彩(qxc)
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.500.com/",
}

def fetch_html(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("gbk", errors="ignore")
        except Exception as e:
            print(f"  抓取失败(第{attempt+1}次): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None

def parse_date_from_html(html):
    """从HTML中提取开奖日期"""
    # 尝试多种日期格式
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            y, mo, da = m.group(1), int(m.group(2)), int(m.group(3))
            if 2020 <= int(y) <= 2030 and 1 <= mo <= 12 and 1 <= da <= 31:
                return f"{y}-{str(mo).zfill(2)}-{str(da).zfill(2)}"
    return ""

def parse_issue_from_html(html):
    """从HTML中提取期号"""
    # 尝试匹配5-7位数字期号
    for m in re.finditer(r'>(\d{5,7})<', html):
        issue = m.group(1)
        # 排除年份等明显不是期号的数字
        if not issue.startswith('202') or len(issue) != 4:
            return issue
    return ""

def extract_balls(html, class_patterns):
    """根据class模式提取号码球"""
    balls = []
    for pat in class_patterns:
        found = re.findall(pat, html)
        balls.extend([int(x) for x in found if x.isdigit()])
    return balls

# ===== 双色球 =====
def fetch_ssq():
    print("[双色球] 开始抓取...")
    url = "https://kaijiang.500.com/ssq.shtml"
    html = fetch_html(url)
    if not html:
        print("[双色球] 抓取失败，跳过")
        return []
    
    issue = parse_issue_from_html(html)
    date = parse_date_from_html(html)
    
    # 提取红球（ball_red）和蓝球（ball_blue）
    red = extract_balls(html, [r'ball_red[^>]*>(\d+)<', r'class="ball[^"]*red[^"]*"[^>]*>(\d+)<'])
    blue = extract_balls(html, [r'ball_blue[^>]*>(\d+)<', r'class="ball[^"]*blue[^"]*"[^>]*>(\d+)<'])
    
    # 去重并保持顺序
    red = list(dict.fromkeys(red))
    blue = list(dict.fromkeys(blue))
    
    if len(red) >= 6 and len(blue) >= 1:
        red = red[:6]
        blue = blue[:1]
        if all(1 <= n <= 33 for n in red) and 1 <= blue[0] <= 16:
            print(f"[双色球] 获取到最新一期: {issue} {date} 红:{red} 蓝:{blue}")
            return [{"issue": issue, "date": date, "red": red, "blue": blue[0]}]
    
    print(f"[双色球] 解析失败 red:{red} blue:{blue}，跳过")
    return []

# ===== 大乐透 =====
def fetch_dlt():
    print("[大乐透] 开始抓取...")
    url = "https://kaijiang.500.com/dlt.shtml"
    html = fetch_html(url)
    if not html:
        print("[大乐透] 抓取失败，跳过")
        return []
    
    issue = parse_issue_from_html(html)
    date = parse_date_from_html(html)
    
    # 提取前区（ball_red）和后区（ball_blue）
    front = extract_balls(html, [r'ball_red[^>]*>(\d+)<', r'class="ball[^"]*red[^"]*"[^>]*>(\d+)<'])
    back = extract_balls(html, [r'ball_blue[^>]*>(\d+)<', r'class="ball[^"]*blue[^"]*"[^>]*>(\d+)<'])
    
    front = list(dict.fromkeys(front))
    back = list(dict.fromkeys(back))
    
    if len(front) >= 5 and len(back) >= 2:
        front = front[:5]
        back = back[:2]
        if all(1 <= n <= 35 for n in front) and all(1 <= n <= 12 for n in back):
            print(f"[大乐透] 获取到最新一期: {issue} {date} 前:{front} 后:{back}")
            return [{"issue": issue, "date": date, "front": front, "back": back}]
    
    print(f"[大乐透] 解析失败 front:{front} back:{back}，跳过")
    return []

# ===== 排列3 =====
def fetch_p3():
    print("[排列3] 开始抓取...")
    url = "https://kaijiang.500.com/pls.shtml"
    html = fetch_html(url)
    if not html:
        print("[排列3] 抓取失败，跳过")
        return []
    
    issue = parse_issue_from_html(html)
    date = parse_date_from_html(html)
    
    # 提取号码（ball_orange 或 ball_red）
    digits = extract_balls(html, [
        r'ball_orange[^>]*>(\d+)<',
        r'ball_red[^>]*>(\d+)<',
        r'class="ball[^"]*"[^>]*>(\d+)<'
    ])
    digits = list(dict.fromkeys(digits))
    
    if len(digits) >= 3:
        digits = digits[:3]
        if all(0 <= n <= 9 for n in digits):
            print(f"[排列3] 获取到最新一期: {issue} {date} {digits}")
            return [{"issue": issue, "date": date, "digits": digits}]
    
    print(f"[排列3] 解析失败 digits:{digits}，跳过")
    return []

# ===== 排列5 =====
def fetch_p5():
    print("[排列5] 开始抓取...")
    url = "https://kaijiang.500.com/plw.shtml"
    html = fetch_html(url)
    if not html:
        print("[排列5] 抓取失败，跳过")
        return []
    
    issue = parse_issue_from_html(html)
    date = parse_date_from_html(html)
    
    digits = extract_balls(html, [
        r'ball_orange[^>]*>(\d+)<',
        r'ball_red[^>]*>(\d+)<',
        r'class="ball[^"]*"[^>]*>(\d+)<'
    ])
    digits = list(dict.fromkeys(digits))
    
    if len(digits) >= 5:
        digits = digits[:5]
        if all(0 <= n <= 9 for n in digits):
            print(f"[排列5] 获取到最新一期: {issue} {date} {digits}")
            return [{"issue": issue, "date": date, "digits": digits}]
    
    print(f"[排列5] 解析失败 digits:{digits}，跳过")
    return []

# ===== 7星彩 =====
def fetch_qxc():
    print("[7星彩] 开始抓取...")
    url = "https://kaijiang.500.com/qxc.shtml"
    html = fetch_html(url)
    if not html:
        print("[7星彩] 抓取失败，跳过")
        return []
    
    issue = parse_issue_from_html(html)
    date = parse_date_from_html(html)
    
    digits = extract_balls(html, [
        r'ball_orange[^>]*>(\d+)<',
        r'class="ball[^"]*"[^>]*>(\d+)<'
    ])
    digits = list(dict.fromkeys(digits))
    
    if len(digits) >= 7:
        digits = digits[:7]
        if all(0 <= n <= 14 for n in digits):
            print(f"[7星彩] 获取到最新一期: {issue} {date} {digits}")
            return [{"issue": issue, "date": date, "digits": digits}]
    
    print(f"[7星彩] 解析失败 digits:{digits}，跳过")
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
    print("彩票开奖数据自动抓取（500彩票网数据源）")
    print(f"数据目录: {DATA_DIR}")
    print("=" * 50)
    updated = False
    
    # 双色球
    if update_lottery("双色球", fetch_ssq, "ssq.json"): updated = True
    print()
    # 大乐透
    if update_lottery("大乐透", fetch_dlt, "dlt.json"): updated = True
    print()
    # 排列3
    if update_lottery("排列3", fetch_p3, "p3.json"): updated = True
    print()
    # 排列5
    if update_lottery("排列5", fetch_p5, "p5.json"): updated = True
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
