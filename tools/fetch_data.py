#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国人口数据平台 — 数据抓取脚本 (阶段 1)

数据源：World Bank Open Data API
- 中国数据由 UN Population Division 估算与各国上报混合而成
- 与统计局口径存在小幅差异，页面上必须标注

策略：不追求实时。抓取一次 -> 校验 -> 固化为 data/*.json。

已知故障模式（2026-10-17 实测）：
  World Bank 源站间歇性返回 502，由 Cloudflare 透传。
  同一 URL 重试若干次即可命中 Cloudflare 缓存（CF-Cache-Status: HIT）后成功。
  因此重试必须使用完全相同的 URL，不要加随机参数——随机化会降低缓存命中率。

用法：
  python fetch_data.py            优先用缓存，缺的才抓
  python fetch_data.py --force    全部重新抓
"""

import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(HERE, "cache")

YEAR_MIN, YEAR_MAX = 1960, 2025
API = ("https://api.worldbank.org/v2/country/CHN/indicator/{code}"
       "?format=json&per_page=400")

# key -> (World Bank 指标代码, 中文名, 单位, 小数位)
INDICATORS = {
    "population": ("SP.POP.TOTL",        "年末总人口",          "人",  0),
    "birth_rate": ("SP.DYN.CBRT.IN",     "出生率",              "‰",  2),
    "death_rate": ("SP.DYN.CDRT.IN",     "死亡率",              "‰",  2),
    "age_0_14":   ("SP.POP.0014.TO.ZS",  "0—14岁人口占比",      "%",  2),
    "age_15_64":  ("SP.POP.1564.TO.ZS",  "15—64岁人口占比",     "%",  2),
    "age_65_up":  ("SP.POP.65UP.TO.ZS",  "65岁及以上人口占比",  "%",  2),
    "urban_rate": ("SP.URB.TOTL.IN.ZS",  "城镇化率",            "%",  2),
    "fertility":  ("SP.DYN.TFRT.IN",     "总和生育率",          "个", 3),
}

BACKOFF = [2, 3, 5, 8, 12, 16, 22, 30]   # 共 8 次尝试


def _parse_rows(rows):
    out = {}
    for r in rows:
        v = r.get("value")
        if v is not None:
            out[int(r["date"])] = v
    return out


def load_cache(code):
    path = os.path.join(CACHE_DIR, code + ".json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)["rows"]
        data = _parse_rows(rows)
        return data if len(data) >= 30 else None      # 太少的缓存视为无效
    except Exception:
        return None


def fetch(code, force=False):
    """返回 ({year: value}, 是否来自缓存)。失败返回 (None, False)。"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, code + ".json")

    if not force:
        cached = load_cache(code)
        if cached:
            print(f"    · 缓存命中 ({len(cached)} 年)")
            return cached, True

    url = API.format(code=code)
    last_err = None

    for attempt, wait in enumerate(BACKOFF, start=1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/120.0 Safari/537.36"),
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=35) as resp:
                body = resp.read().decode("utf-8", "replace")

            payload = json.loads(body)
            if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
                raise ValueError("payload 为空")

            data = _parse_rows(payload[1])
            if len(data) < 10:
                raise ValueError(f"有效值过少 ({len(data)})")

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(),
                           "code": code, "rows": payload[1]},
                          f, ensure_ascii=False)
            print(f"    = ok ({len(data)} 年，第 {attempt} 次尝试)")
            return data, False

        except Exception as e:
            last_err = f"{type(e).__name__}"
            if attempt < len(BACKOFF):
                jitter = random.uniform(0, 1.5)
                print(f"    ! {attempt}/{len(BACKOFF)} {last_err}，{wait}s 后重试")
                time.sleep(wait + jitter)
            else:
                print(f"    x {len(BACKOFF)} 次尝试全部失败 ({last_err})")

    stale = load_cache(code)          # 最后兜底：用过期缓存
    if stale:
        print("    ~ 回落到旧缓存")
        return stale, True
    return None, False


def main():
    force = "--force" in sys.argv
    os.makedirs(DATA_DIR, exist_ok=True)

    series, provenance, failed = {}, {}, []

    print("[1/3] 抓取指标" + ("（强制刷新）" if force else "（缓存优先）"))
    for key, (code, label, unit, digits) in INDICATORS.items():
        print(f"  - {key:12s} {code}")
        data, from_cache = fetch(code, force=force)
        if data is None:
            failed.append(key)
            print(f"    !! {key} 无数据，跳过")
            continue
        series[key] = {
            "label": label, "unit": unit, "digits": digits,
            "data": {str(y): round(v, digits) for y, v in sorted(data.items())},
        }
        provenance[key] = {"code": code, "from_cache": from_cache}
        time.sleep(1.5 + random.uniform(0, 1.5))

    if not series:
        print("\n没有取到任何数据，中止。")
        sys.exit(1)

    print("\n[2/3] 计算派生指标")
    pop = series.get("population", {}).get("data", {})
    if pop:
        growth = {}
        years = sorted(int(y) for y in pop)
        for i in range(1, len(years)):
            y, prev = years[i], years[i - 1]
            if y - prev == 1:
                growth[str(y)] = pop[str(y)] - pop[str(prev)]
        series["annual_change"] = {
            "label": "年增量", "unit": "人", "digits": 0, "data": growth,
            "derived": "年末总人口逐年差分",
        }
        print(f"    = annual_change ({len(growth)} 年)")

    br = series.get("birth_rate", {}).get("data", {})
    dr = series.get("death_rate", {}).get("data", {})
    if br and dr:
        ngr = {y: round(br[y] - dr[y], 2) for y in br if y in dr}
        series["natural_rate"] = {
            "label": "自然增长率", "unit": "‰", "digits": 2, "data": ngr,
            "derived": "出生率 − 死亡率",
        }
        print(f"    = natural_rate ({len(ngr)} 年)")

    print("\n[3/3] 写入 JSON")
    out = {
        "meta": {
            "title": "中国人口数据",
            "country": "中国 (CHN)",
            "source_name": "World Bank Open Data",
            "source_url": "https://data.worldbank.org/country/china",
            "api_endpoint": "https://api.worldbank.org/v2/country/CHN/indicator/",
            "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "year_range": [YEAR_MIN, YEAR_MAX],
            "caveat": ("World Bank 中国数据由 UN 人口司估算与各国上报混合而成，"
                       "与中国国家统计局口径存在小幅差异"
                       "（如 2024 年末人口：统计局口径 14.08 亿，WB 14.08975 亿）。"
                       "引用时请注明来源与口径。"),
            "license": "World Bank Open Data, CC BY 4.0",
        },
        "provenance": provenance,
        "failed": failed,
        "series": series,
    }

    path = os.path.join(DATA_DIR, "national.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\n完成 -> {path}  ({os.path.getsize(path)/1024:.1f} KB)")

    print("\n数据体检：")
    for k, v in series.items():
        ys = sorted(int(y) for y in v["data"])
        print(f"  {k:14s} {len(ys):3d} 年  {ys[0]}–{ys[-1]}  "
              f"最新 {v['data'][str(ys[-1])]}")

    if failed:
        print(f"\n缺失指标：{', '.join(failed)}")
        print("重新运行本脚本即可只补抓缺失项（已成功的走缓存）。")
        sys.exit(2)


if __name__ == "__main__":
    main()
