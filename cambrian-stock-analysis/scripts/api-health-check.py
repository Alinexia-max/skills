#!/usr/bin/env python3
"""
寒武纪鳄鱼策略 - API 端点可用性自动检测脚本

功能：
  1. 测试 api-endpoints.md 中注册的所有 API 端点
  2. 输出 JSON 格式的可用性报告
  3. --update 模式：自动更新 api-endpoints.md 中的 ✅/❌ 标记

用法：
  python3 scripts/api-health-check.py              # 仅检测，输出 JSON
  python3 scripts/api-health-check.py --update     # 检测并自动更新 api-endpoints.md
  python3 scripts/api-health-check.py --json       # 仅检测，纯 JSON 输出（管道友好）

返回 JSON 结构：
  {
    "timestamp": "2025-01-01T00:00:00",
    "endpoints": {
      "实时行情": {
        "eastmoney": {"status": "available", "url": "...", "latency_ms": 123},
        "tencent": {"status": "available", "url": "...", "latency_ms": 200},
        "sina": {"status": "unavailable", "url": "...", "error": "403 Forbidden"}
      },
      ...
    },
    "summary": {
      "total": 11, "available": 9, "unavailable": 2,
      "changes": [{"name": "sina", "old": "available", "new": "unavailable"}]
    }
  }
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ─── 端点注册表 ───────────────────────────────────────────────

ENDPOINTS = {
    "实时行情": {
        "eastmoney": {
            "label": "东方财富实时行情 (#1)",
            "url": "https://push2.eastmoney.com/api/qt/stock/get?secid=0.000001&fields=f57,f58,f43",
            "method": "GET",
            "valid_check": lambda resp: '"data"' in resp and '"f57"' in resp,
        },
        "tencent": {
            "label": "腾讯实时行情 (#2)",
            "url": "https://qt.gtimg.cn/q=sz000001",
            "method": "GET",
            "valid_check": lambda resp: "v_sz000001" in resp,
        },
        "sina": {
            "label": "新浪实时行情 (#3)",
            "url": "https://hq.sinajs.cn/list=sz000001",
            "method": "GET",
            "headers": {"Referer": "https://finance.sina.com.cn"},
            "valid_check": lambda resp: "sz000001" in resp and "var " not in resp[:50],
        },
    },
    "基本面": {
        "company_survey": {
            "label": "公司概况 (#4)",
            "url": "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code=SZ000001",
            "method": "GET",
            "valid_check": lambda resp: '"jbzl"' in resp,
        },
        "business_analysis": {
            "label": "营收构成 (#5)",
            "url": "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SZ000001",
            "method": "GET",
            "valid_check": lambda resp: '"zygcfx"' in resp or '"MAIN_BUSINESS_INCOME"' in resp,
        },
        "shareholder": {
            "label": "股东统计 (#6)",
            "url": "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code=SZ000001&type=skg",
            "method": "GET",
            "valid_check": lambda resp: '"gdrs"' in resp or '"data"' in resp,
        },
    },
    "财务数据": {
        "income_statement": {
            "label": "利润表 datacenter (#7)",
            "url": (
                "https://datacenter.eastmoney.com/securities/api/data/v1/get"
                "?reportName=RPT_DMSK_FN_INCOME"
                "&columns=SECURITY_CODE,REPORT_DATE,PARENT_NETPROFIT"
                "&filter=(SECURITY_CODE%3D%22000001%22)"
                "&pageNumber=1&pageSize=2&sortTypes=-1&sortColumns=REPORT_DATE"
            ),
            "method": "GET",
            "valid_check": lambda resp: '"result"' in resp and '"PARENT_NETPROFIT"' in resp,
        },
        "sina_finance": {
            "label": "新浪利润表 (#8)",
            "url": "https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_ProfitStatement/stockid/000001/ctrl/part/displaytype/4.phtml",
            "method": "GET",
            "valid_check": lambda resp: len(resp) > 1000 and "利润表" in resp,
        },
    },
    "K线数据": {
        "daily_kline": {
            "label": "日K线 push2his (#9)",
            "url": (
                "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                "?secid=0.000001&fields1=f1,f2,f3&fields2=f51,f52,f53"
                "&klt=101&fqt=0&end=20500101&lmt=5"
            ),
            "method": "GET",
            "valid_check": lambda resp: '"data"' in resp and '"klines"' in resp,
        },
        "monthly_kline": {
            "label": "月K线 klt=103 (#10)",
            "url": (
                "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                "?secid=0.000001&fields1=f1,f2,f3&fields2=f51,f52,f53"
                "&klt=103&fqt=0&end=20500101&lmt=5"
            ),
            "method": "GET",
            "valid_check": lambda resp: resp and '"klines"' in resp and len(resp) > 100,
        },
        "weekly_kline": {
            "label": "周K线 klt=102 (#11)",
            "url": (
                "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                "?secid=0.000001&fields1=f1,f2,f3&fields2=f51,f52,f53"
                "&klt=102&fqt=0&end=20500101&lmt=5"
            ),
            "method": "GET",
            "valid_check": lambda resp: resp and '"klines"' in resp and len(resp) > 100,
        },
    },
}


def fetch(url, headers=None, timeout=10):
    """发起 HTTP GET 请求，返回 (status, body, latency_ms, error_msg)."""
    t0 = time.time()
    req_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    last_error = None
    for attempt in range(3):  # 最多重试 3 次
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body_raw = resp.read()
                # 尝试 utf-8-sig (BOM) 再 fallback utf-8
                try:
                    body = body_raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    body = body_raw.decode("gbk", errors="replace")
                latency = (time.time() - t0) * 1000
                return "ok", body, int(latency), None
        except urllib.error.HTTPError as e:
            latency = (time.time() - t0) * 1000
            body = e.read().decode("utf-8", errors="replace")[:500]
            return "http_error", body, int(latency), f"HTTP {e.code}"
        except urllib.error.URLError as e:
            last_error = str(e.reason)
            if attempt < 2:
                time.sleep(1 + attempt)  # 递增等待
                t0 = time.time()  # 重置计时
                continue
            latency = (time.time() - t0) * 1000
            return "network_error", "", int(latency), last_error
        except Exception as e:
            latency = (time.time() - t0) * 1000
            return "error", "", int(latency), str(e)


def test_all_endpoints(verbose=False):
    """测试所有注册端点，返回完整报告 dict。"""
    results = {}
    changes = []
    total, available_count = 0, 0

    for category, endpoints in ENDPOINTS.items():
        results[category] = {}
        for key, info in endpoints.items():
            total += 1
            status, body, latency, error = fetch(
                info["url"], headers=info.get("headers"), timeout=10
            )

            is_valid = False
            if status == "ok" and body:
                try:
                    is_valid = info["valid_check"](body)
                except Exception:
                    is_valid = False

            if is_valid:
                avail = "available"
                available_count += 1
            else:
                avail = "unavailable"

            entry = {
                "label": info["label"],
                "url": info["url"][:200],
                "status": avail,
                "latency_ms": latency,
            }
            if error:
                entry["error"] = error
            if avail == "unavailable" and status == "ok" and not is_valid:
                # 能连上但内容不符 — 可能是 API 改版
                entry["error"] = "response validation failed"
                entry["response_preview"] = body[:200]

            results[category][key] = entry

            if verbose:
                emoji = "✅" if avail == "available" else "❌"
                print(f"  {emoji} {info['label']}: {avail} ({latency}ms)" + (f" — {error}" if error else ""))

    summary = {
        "total": total,
        "available": available_count,
        "unavailable": total - available_count,
        "changes": changes,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": results,
        "summary": summary,
    }


def read_api_doc(path: Path) -> str:
    """读取 api-endpoints.md 内容。"""
    return path.read_text(encoding="utf-8")


def update_status_in_doc(content: str, report: dict) -> tuple[str, list]:
    """
    根据检测结果更新 api-endpoints.md 中的 ✅/❌ 标记。
    返回 (更新后的内容, 变更列表)。
    """
    changes = []
    updated = content

    # 端点名 → 文件中行关键词（不含 emoji）
    label_to_target = {
        "东方财富实时行情 (#1)": "东方财富实时行情",
        "腾讯实时行情 (#2)": "腾讯实时行情",
        "新浪实时行情 (#3)": "新浪实时行情",
        "公司概况 (#4)": "公司概况",
        "营收构成 (#5)": "营收构成（主营占比）",
        "股东统计 (#6)": "股东人数统计",
        "利润表 datacenter (#7)": "利润表（归母净利润）",
        "新浪利润表 (#8)": "新浪利润表",
        "日K线 push2his (#9)": "日K线",
        "月K线 klt=103 (#10)": "月K线",
        "周K线 klt=102 (#11)": "周K线",
    }

    for category, endpoints in report["endpoints"].items():
        for key, entry in endpoints.items():
            label = entry["label"]
            new_status = entry["status"]
            target = label_to_target.get(label)
            if not target:
                continue

            # 在文件中找到包含 target 的行并提取当前标记
            new_mark = "✅" if new_status == "available" else "❌"
            for i, line in enumerate(updated.split("\n")):
                if target in line and ("###" in line or "标记" in line):
                    # 确保我们匹配到的是端点标题行
                    old_mark = ""
                    if "✅" in line:
                        old_mark = "✅"
                    elif "❌" in line:
                        old_mark = "❌"
                    elif "⚠" in line or "⚠️" in line:
                        old_mark = "⚠️" if "⚠️" in line else "⚠"

                    if old_mark and old_mark != new_mark:
                        # 确定旧状态的语义
                        if old_mark in ("⚠", "⚠️"):
                            old_status = "warning"
                        elif old_mark == "✅":
                            old_status = "available"
                        else:
                            old_status = "unavailable"
                        changes.append(
                            {
                                "endpoint": label,
                                "old": old_status,
                                "new": new_status,
                            }
                        )
                        # 只替换该行中的 emoji
                        updated = updated.replace(
                            f"{target} {old_mark}", f"{target} {new_mark}"
                        )
                    break

    return updated, changes


def parse_existing_status(content: str) -> dict:
    """从 api-endpoints.md 中提取现有端点状态。"""
    status_map = {}
    # 匹配 ### #N 标题行中的 ✅/❌/⚠
    pattern = re.compile(r"### #(\d+)\s+(.+?)\s+([✅❌⚠])")
    for m in pattern.finditer(content):
        num, name, mark = m.group(1), m.group(2), m.group(3)
        status = "available" if mark in ["✅", "⚠"] else "unavailable"
        status_map[num] = {"name": name.strip(), "status": status, "mark": mark}
    return status_map


def main():
    import argparse

    parser = argparse.ArgumentParser(description="API 端点可用性检测")
    parser.add_argument(
        "--update",
        action="store_true",
        help="检测后自动更新 api-endpoints.md 中的可用性标记",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="纯 JSON 输出（适合管道传递给其他脚本）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="打印详细检测进度",
    )
    args = parser.parse_args()

    if args.verbose:
        print("🔍 正在检测 API 端点可用性...\n")

    report = test_all_endpoints(verbose=args.verbose)

    skill_dir = Path(__file__).resolve().parent.parent
    api_doc_path = skill_dir / "references" / "api-endpoints.md"

    if args.update and api_doc_path.exists():
        old_content = read_api_doc(api_doc_path)
        new_content, changes = update_status_in_doc(old_content, report)
        report["summary"]["changes"] = changes
        if changes:
            api_doc_path.write_text(new_content, encoding="utf-8")
            if args.verbose:
                print(f"\n📝 已更新 {len(changes)} 处端点状态到 {api_doc_path}")
                for c in changes:
                    old_emoji = "✅" if c["old"] == "available" else "❌"
                    new_emoji = "✅" if c["new"] == "available" else "❌"
                    print(f"   {old_emoji} → {new_emoji} {c['endpoint']}")
        else:
            if args.verbose:
                print(f"\n✅ 所有端点状态未变化，无需更新")

    # 输出结果
    out = {
        "timestamp": report["timestamp"],
        "summary": report["summary"],
        "endpoints": {},
    }
    for cat, eps in report["endpoints"].items():
        out["endpoints"][cat] = {
            k: {"status": v["status"], "latency_ms": v.get("latency_ms", 0), "error": v.get("error", "")}
            for k, v in eps.items()
        }

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
