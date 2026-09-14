#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票数据自动更新脚本（无第三方依赖版 v2）
仅使用 Python 标准库 urllib，无需 pip install
功能：获取最新开奖数据 → 与本地数据合并去重 → 保存
支持：双色球、大乐透、3D、排列3、排列5、七星彩、快乐8
"""

import urllib.request
import json
import os
import time

# ===== 配置 =====
DATA_DIR = "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.cwl.gov.cn/"
}


def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  请求失败: {e}")
        return None


def fetch_cwl(api_name, count=10):
    """福彩官网：双色球ssq、3D、快乐8kl8"""
    url = f"https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name={api_name}&issueCount={count}"
    text = fetch_url(url)
    if not text:
        return []
    try:
        data = json.loads(text)
        result = []
        for item in data.get("result", []):
            red = [int(x) for x in item.get("red", "").split(",") if x.strip()]
            blue_str = item.get("blue", "")
            entry = {
                "issue": item.get("code", ""),
                "date": item.get("date", "")[:10],
                "red": red
            }
            if blue_str:
                blue_list = [int(x) for x in blue_str.split(",") if x.strip()]
                entry["blue"] = blue_list[0] if len(blue_list) == 1 else blue_list
            result.append(entry)
        return result
    except Exception as e:
        print(f"  解析失败: {e}")
        return []


def fetch_sporttery(game_no, count=10, is_dlt=False):
    """体彩官网：大乐透gameNo=85、排列3=35、排列5=35、七星彩=04"""
    url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo={game_no}&provinceId=0&pageSize={count}&isVerify=1&pageNo=1"
    text = fetch_url(url)
    if not text:
        return []
    try:
        data = json.loads(text)
        result = []
        for item in data.get("value", {}).get("list", []):
            draw_result = item.get("lotteryDrawResult", "")
            draw_time = item.get("lotteryDrawTime", "")
            issue = item.get("lotteryDrawNum", "")
            if is_dlt:
                # 大乐透格式: "01 02 03 04 05 + 06 07"
                parts = draw_result.replace("+", " ").split()
                parts = [p for p in parts if p.strip()]
                front = sorted([int(x) for x in parts[:5]]) if len(parts) >= 5 else []
                back = sorted([int(x) for x in parts[5:7]]) if len(parts) >= 7 else []
                result.append({"issue": issue, "date": draw_time, "front": front, "back": back})
            else:
                nums = [int(x) for x in draw_result.replace(" ", "") if x.isdigit()]
                result.append({"issue": issue, "date": draw_time, "red": nums})
        return result
    except Exception as e:
        print(f"  解析失败: {e}")
        return []


def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_and_dedup(existing, new_data):
    """合并数据，按期号去重，降序排列"""
    issues = {item.get("issue") for item in existing}
    merged = list(existing)
    added = 0
    for item in new_data:
        issue = item.get("issue")
        if issue and issue not in issues:
            merged.append(item)
            issues.add(issue)
            added += 1
    merged.sort(key=lambda x: x.get("issue", ""), reverse=True)
    return merged, added


def update_one(name, fetch_func, filename):
    print(f"\n--- {name} ---")
    filepath = os.path.join(DATA_DIR, filename)
    new_data = fetch_func()
    if not new_data:
        print("  未获取到数据")
        return 0
    print(f"  获取到 {len(new_data)} 期，最新: {new_data[0].get('issue')}")
    existing = load_json(filepath)
    print(f"  本地已有 {len(existing)} 期")
    merged, added = merge_and_dedup(existing, new_data)
    if added > 0:
        save_json(filepath, merged)
        print(f"  新增 {added} 期，已保存")
    else:
        print("  已是最新，无需更新")
    return added


def main():
    print("=" * 50)
    print("彩票数据自动更新（无依赖版 v2）")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    os.makedirs(DATA_DIR, exist_ok=True)
    total = 0

    # 福彩
    total += update_one("双色球", lambda: fetch_cwl("ssq", 10), "ssq.json")
    time.sleep(1)
    total += update_one("3D", lambda: fetch_cwl("3d", 10), "3d.json")
    time.sleep(1)
    total += update_one("快乐8", lambda: fetch_cwl("kl8", 10), "kl8.json")
    time.sleep(1)

    # 体彩
    total += update_one("大乐透", lambda: fetch_sporttery(85, 10, True), "dlt.json")
    time.sleep(1)
    total += update_one("排列3", lambda: fetch_sporttery(35, 10), "pl3.json")
    time.sleep(1)
    total += update_one("排列5", lambda: fetch_sporttery(35, 10), "pl5.json")
    time.sleep(1)
    total += update_one("七星彩", lambda: fetch_sporttery(4, 10), "qxc.json")

    print(f"\n{'=' * 50}")
    print(f"更新完成！共新增 {total} 期")
    print("=" * 50)

    # GitHub Actions 输出
    print(f"::set-output name=updated::{'true' if total > 0 else 'false'}")
    print(f"::set-output name=total_added::{total}")


if __name__ == "__main__":
    main()
#（注：内容由AI生成）
