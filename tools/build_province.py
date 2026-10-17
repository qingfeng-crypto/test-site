#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分省人口数据构建 (2020 年第七次全国人口普查)

数据来源：国家统计局《第七次全国人口普查公报（第三号）—— 地区人口情况》
         2021 年 5 月 11 日发布
         https://www.stats.gov.cn/zt_18555/zdtjgz/zgrkpc/dqcrkpc/ggl/202302/t20230215_1903999.html

数据为手工录入的公报原文数字，脚本负责规范化与总量校验。
校验规则：31 省合计 + 现役军人 200 万 必须等于公报全国总人口 1,411,778,724。
不通过则拒绝写文件 —— 宁可报错，不留错数。
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "province.json")

# 名称与 adcode 与 DataV 省级边界数据保持一致
PROVINCES = [
    ("北京市", 110000, 21893095),
    ("天津市", 120000, 13866009),
    ("河北省", 130000, 74610235),
    ("山西省", 140000, 34915616),
    ("内蒙古自治区", 150000, 24049155),
    ("辽宁省", 210000, 42591407),
    ("吉林省", 220000, 24073453),
    ("黑龙江省", 230000, 31850088),
    ("上海市", 310000, 24870895),
    ("江苏省", 320000, 84748016),
    ("浙江省", 330000, 64567588),
    ("安徽省", 340000, 61027171),
    ("福建省", 350000, 41540086),
    ("江西省", 360000, 45188635),
    ("山东省", 370000, 101527453),
    ("河南省", 410000, 99365519),
    ("湖北省", 420000, 57752557),
    ("湖南省", 430000, 66444864),
    ("广东省", 440000, 126012510),
    ("广西壮族自治区", 450000, 50126804),
    ("海南省", 460000, 10081232),
    ("重庆市", 500000, 32054159),
    ("四川省", 510000, 83674866),
    ("贵州省", 520000, 38562148),
    ("云南省", 530000, 47209277),
    ("西藏自治区", 540000, 3648100),
    ("陕西省", 610000, 39528999),
    ("甘肃省", 620000, 25019831),
    ("青海省", 630000, 5923957),
    ("宁夏回族自治区", 640000, 7202654),
    ("新疆维吾尔自治区", 650000, 25852345),
]

SERVICEMEN = 2000000
NATIONAL_TOTAL = 1411778724


def main():
    total = sum(p[2] for p in PROVINCES)
    grand = total + SERVICEMEN

    print(f"31 省合计      : {total:,}")
    print(f"现役军人       : {SERVICEMEN:,}")
    print(f"合计           : {grand:,}")
    print(f"公报全国总人口 : {NATIONAL_TOTAL:,}")

    if grand != NATIONAL_TOTAL:
        print(f"\n[校验失败] 差额 {grand - NATIONAL_TOTAL:+,} 人，拒绝写出文件。")
        sys.exit(1)
    print("[校验通过] 分省合计与公报全国总人口完全吻合。")

    rows = []
    for name, adcode, pop in PROVINCES:
        rows.append({
            "name": name,
            "adcode": adcode,
            "population": pop,
            "share": round(pop / NATIONAL_TOTAL * 100, 2),
        })
    rows.sort(key=lambda r: -r["population"])

    out = {
        "meta": {
            "title": "分省人口",
            "year": 2020,
            "reference_date": "2020-11-01T00:00:00",
            "source_name": "国家统计局《第七次全国人口普查公报（第三号）》",
            "source_url": ("https://www.stats.gov.cn/zt_18555/zdtjgz/zgrkpc/"
                           "dqcrkpc/ggl/202302/t20230215_1903999.html"),
            "published": "2021-05-11",
            "national_total": NATIONAL_TOTAL,
            "servicemen": SERVICEMEN,
            "caveat": ("数据为普查初步汇总数据；全国总人口含 31 个省级单位常住人口与现役军人，"
                       "不含香港、澳门特别行政区和台湾地区人口，也不含居住在内地的外籍人员。"
                       "常住人口口径：居住在本乡镇街道且户口在本乡镇街道或户口待定的人等五类。"),
        },
        "provinces": rows,
        "checksum": {"sum_provinces": total, "plus_servicemen": grand,
                     "matches_published": grand == NATIONAL_TOTAL},
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\n写出 -> {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)")
    print("\n前五：")
    for r in rows[:5]:
        print(f"  {r['name']:12s} {r['population']:>12,}  {r['share']:>5.2f}%")


if __name__ == "__main__":
    main()
