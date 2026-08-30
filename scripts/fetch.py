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
    for m in re.finditer(r'>(\d{5,7})<', html):
        issue = m.group(1)
        if not (issue.startswith('202') and len(issue) == 4):
            return issue
    return ""

def extract_all_balls(html):
    """提取所有号码球（不去重，保持顺序）"""
    balls = []
    # 匹配各种class的号码球
    patterns = [
        r'class="ball[^"]*"[^>]*>(\d+)<',
        r'class="qiu[^"]*"[^>]*>(\d+)<',
        r'class="num[^"]*"[^>]*>(\d+)<',
        r'class="hao[^"]*"[^>]*>(\d+)<',
        r'class="code[^"]*"[^>]*>(\d+)<',
        r'<li[^>]*>(\d{1,2})</li>',
        r'<li[^>]*class="[^"]*"[^>]*>(\d{1,2})<',
        r'<em[^>]*>(\d+)</em>',
        r'<i[^>]*>(\d+)</i>',
        r'<span[^>]*>(\d{1,2})</span>',
        r'<div[^>]*class="[^"]*ball[^"]*"[^>]*>(\d+)<',
    ]
    for pat in patterns:
        found = re.findall(pat, html)
        for x in found:
            if x.isdigit() and len(x) <= 2:
                n = int(x)
                if 0 <= n <= 35:
                    balls.append(n)
    
    # 如果上面的方法没找到，直接提取所有两位数字（01-35）
    if not balls:
        all_digits = re.findall(r'\b(\d{2})\b', html)
        for x in all_digits:
            n = int(x)
            if 1 <= n <= 35:
                balls.append(n)
    
    return balls

def extract_lotto_balls(html, red_count, blue_count, red_max, blue_max):
    """提取乐透型号码（去重）"""
    all_balls = extract_all_balls(html)
    
    # 去重但保持顺序
    seen = set()
    unique = []
    for n in all_balls:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    
    # 方法1：尝试找到连续的 red_count+blue_count 个数字，符合红蓝区间
    total = red_count + blue_count
    for i in range(len(unique) - total + 1):
        candidate = unique[i:i+total]
        red_part = candidate[:red_count]
        blue_part = candidate[red_count:]
        if all(1 <= n <= red_max for n in red_part) and all(1 <= n <= blue_max for n in blue_part):
            return red_part, blue_part
    
    # 方法2：按区间筛选
    red_valid = [n for n in unique if 1 <= n <= red_max]
    blue_valid = [n for n in unique if 1 <= n <= blue_max]
    
    if len(red_valid) >= red_count and len(blue_valid) >= blue_count:
        red = red_valid[:red_count]
        # 蓝球从不在红球中的数字里取
        remaining = [n for n in blue_valid if n not in red]
        blue = remaining[:blue_count] if remaining else blue_valid[:blue_count]
        return red, blue
    
    return [], []

def extract_digit_balls(html, count):
    """提取数字型号码（不去重）"""
    all_balls = extract_all_balls(html)
    # 数字型只取0-9
    digits = [n for n in all_balls if 0 <= n <= 9]
    if len(digits) >= count:
        return digits[:count]
    return digits

# ===== 双色球（福彩官网API）=====
def fetch_ssq():
    print("[双色球] 开始抓取...")
    
    # 方法1：福彩官网API（加Referer）
    try:
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=1"
        headers = dict(HEADERS)
        headers["Referer"] = "https://www.cwl.gov.cn/ygkj/wqkjgg/ssq/"
        headers["Host"] = "www.cwl.gov.cn"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data and data.get("state") == 0:
            result = data.get("result", [])
            if result:
                item = result[0]
                issue = item.get("code", "")
                date = item.get("date", "").split("(")[0].strip()
                red = [int(x) for x in item.get("red", "").split(",")]
                blue = [int(item.get("blue", "0"))]
                if len(red) == 6 and len(blue) == 1:
                    if all(1 <= n <= 33 for n in red) and 1 <= blue[0] <= 16:
                        print(f"[双色球] 从福彩API获取到: {issue} {date} 红:{red} 蓝:{blue}")
                        return [{"issue": issue, "date": date, "red": red, "blue": blue[0]}]
    except Exception as e:
        print(f"[双色球] 福彩API抓取失败: {e}")
    
    # 方法2：500彩票网历史数据（和大乐透同样的方法）
    try:
        url = "https://datachart.500.com/ssq/history/newinc/history.php?start=2026001&end=2026999"
        html = fetch_html(url)
        if html:
            rows = re.findall(r'<tr[^>]*class="t_tr1"[^>]*>(.*?)</tr>', html, re.DOTALL)
            if not rows:
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            for row in rows[:10]:
                # 提取所有数字（包括在各种标签中的）
                nums = [int(x) for x in re.findall(r'>(\d{1,2})<', row)]
                if len(nums) >= 8:
                    # 找期号（7位）
                    issue_match = re.search(r'>(\d{7})<', row)
                    if issue_match:
                        issue = issue_match.group(1)
                        red = nums[:6]
                        blue = [nums[6]]
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', row)
                        date = date_match.group(1) if date_match else ""
                        if all(1 <= n <= 33 for n in red) and 1 <= blue[0] <= 16:
                            print(f"[双色球] 从500历史数据获取到: {issue} {date} 红:{red} 蓝:{blue}")
                            return [{"issue": issue, "date": date, "red": red, "blue": blue[0]}]
    except Exception as e:
        print(f"[双色球] 500历史数据抓取失败: {e}")
    
    print(f"[双色球] 解析失败，跳过")
    return []

# ===== 大乐透（从500彩票网历史数据抓取）=====
def fetch_dlt():
    print("[大乐透] 开始抓取...")
    url = "https://datachart.500.com/dlt/history/newinc/history.php?start=26001&end=26999"
    html = fetch_html(url)
    if not html:
        print("[大乐透] 抓取失败，跳过")
        return []
    
    rows = re.findall(r'<tr[^>]*class="t_tr1"[^>]*>(.*?)</tr>', html, re.DOTALL)
    if not rows:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    
    for row in rows[:5]:
        # 提取期号：从链接或第一个td中提取5位数字
        issue_match = re.search(r'<a[^>]*>(26\d{3})</a>', row)
        if not issue_match:
            issue_match = re.search(r'>(26\d{3})<', row)
        if not issue_match:
            issue_match = re.search(r'>(\d{5})<', row)
        
        if not issue_match:
            continue
            
        issue = issue_match.group(1)
        
        # 提取所有号码数字（排除期号）
        all_nums = [int(x) for x in re.findall(r'>(\d{1,2})<', row)]
        # 排除期号相关数字
        issue_int = int(issue)
        nums = [n for n in all_nums if n != issue_int and n != int(issue[-3:])]
        
        # 前5个是前区，后2个是后区
        if len(nums) >= 7:
            front = nums[:5]
            back = nums[5:7]
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', row)
            date = date_match.group(1) if date_match else ""
            
            if len(front) == 5 and len(back) == 2:
                if all(1 <= n <= 35 for n in front) and all(1 <= n <= 12 for n in back):
                    print(f"[大乐透] 获取到最新一期: {issue} {date} 前:{front} 后:{back}")
                    return [{"issue": issue, "date": date, "front": front, "back": back}]
    
    print(f"[大乐透] 解析失败，跳过")
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
    digits = extract_digit_balls(html, 3)
    
    if len(digits) == 3:
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
    digits = extract_digit_balls(html, 5)
    
    if len(digits) == 5:
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
    # 7星彩前6位是0-9，最后一位是0-14
    all_balls = extract_all_balls(html)
    digits = [n for n in all_balls if 0 <= n <= 14]
    
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
    print("彩票开奖数据自动抓取")
    print(f"数据目录: {DATA_DIR}")
    print("=" * 50)
    updated = False
    
    # 双色球暂时禁用（福彩API 403，500彩票网页面结构解析不了）
    # if update_lottery("双色球", fetch_ssq, "ssq.json"): updated = True
    # print()
    
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
