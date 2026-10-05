#!/usr/bin/env python3
r"""
寒武纪鳄鱼策略 - 数据来源自检脚本

数据来源已改为「westock 优先」：
  - 主源：westock CLI（覆盖行情/财务/K线/股东/简况等全部定量数据）
  - 缺口：仅 #5 营收构成、#4 公司概况 两个端点保留 HTTP

本脚本因此只检查三件事：
  1. westock CLI 是否可用、版本是否正确
  2. 缺口端点 #5 营收构成 是否可用
  3. 缺口端点 #4 公司概况 是否可用

用法：
  python3 scripts/api-health-check.py           # macOS / Linux
  python  scripts/api-health-check.py           # Windows（或 py）
  python  scripts/api-health-check.py --json    # 纯 JSON 输出（管道友好）
  python  scripts/api-health-check.py -v        # 详细进度

注意（Windows）：用 python 或 py，不要用 python3 —— 本机 python3 是
      Microsoft Store 的假快捷方式，执行会报 "Python was not found"；
      可用的是 D:\python\Python314\python.exe（Python 3.14.7）。

退出码：
  0 = westock 可用（缺口端点失败不算致命，会走"数据不可得"规则）
  1 = westock 不可用（主源失效，无法分析）
"""

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

# ─── 配置 ─────────────────────────────────────────────────────

EXPECTED_WESTOCK_VERSION = "0.0.6"

# westock 未在 PATH 时的绝对路径兜底
WESTOCK_FALLBACK = r"C:\Users\LENOVO\.local\bin\westock.exe"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# 仅这两个缺口端点允许保留（见 SKILL.md 数据来源铁律 规则二）
GAP_ENDPOINTS = [
    {
        "key": "revenue_composition",
        "label": "#5 营收构成（因子 #5 唯一来源）",
        "url": "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SZ000928",
        "needle": "zygcfx",
        "timeout": 20,
    },
    {
        "key": "company_survey",
        "label": "#4 公司概况（实控人兜底）",
        "url": "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code=SZ000928",
        "needle": "jbzl",
        "timeout": 45,  # 该接口实测 10s+，超时须放宽
    },
]


# ─── westock 主源检查 ─────────────────────────────────────────

def resolve_westock():
    """返回 (可执行路径, 来源说明)。优先 PATH，其次绝对路径兜底。"""
    found = shutil.which("westock")
    if found:
        return found, "PATH"
    import os
    if os.path.exists(WESTOCK_FALLBACK):
        return WESTOCK_FALLBACK, "absolute-fallback"
    return None, "not-found"


def check_westock():
    exe, source = resolve_westock()
    if not exe:
        return {
            "status": "unavailable",
            "error": "westock 既不在 PATH，也不在兜底路径",
            "path": None,
        }
    t0 = time.time()
    try:
        out = subprocess.run(
            [exe, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        latency = int((time.time() - t0) * 1000)
        text = (out.stdout or "") + (out.stderr or "")
        ok = out.returncode == 0 and "westock" in text
        version_ok = EXPECTED_WESTOCK_VERSION in text
        return {
            "status": "available" if ok else "unavailable",
            "path": exe,
            "resolved_via": source,
            "version_raw": text.strip(),
            "version_expected": EXPECTED_WESTOCK_VERSION,
            "version_match": version_ok,
            "latency_ms": latency,
            "returncode": out.returncode,
            "error": "" if ok else text.strip()[:200],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "unavailable",
            "path": exe,
            "resolved_via": source,
            "error": str(e),
        }


# ─── 缺口端点检查 ─────────────────────────────────────────────

def fetch(url, timeout):
    """GET 请求并返回 (status, text, latency_ms, error)。

    注意：东财端点会返回 gzip 压缩内容，urllib 不会自动解压，
    必须按 Content-Encoding 手动 gunzip，否则会误判为"响应中未找到关键词"。
    """
    t0 = time.time()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            encoding = (resp.headers.get("Content-Encoding") or "").lower()
            if "gzip" in encoding:
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass  # 已解压或非 gzip，按原样处理
            elif raw[:2] == b"\x1f\x8b":
                # 服务端未声明但实际是 gzip
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
            try:
                body = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                body = raw.decode("gbk", errors="replace")
            return "ok", body, int((time.time() - t0) * 1000), None
    except urllib.error.HTTPError as e:
        return "http_error", "", int((time.time() - t0) * 1000), f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "error", "", int((time.time() - t0) * 1000), str(e)


def check_gap(ep):
    status, body, latency, error = fetch(ep["url"], ep["timeout"])
    valid = status == "ok" and ep["needle"] in body
    entry = {
        "label": ep["label"],
        "status": "available" if valid else "unavailable",
        "latency_ms": latency,
    }
    if error:
        entry["error"] = error
    elif not valid:
        entry["error"] = f"响应中未找到 '{ep['needle']}'"
    return entry


# ─── 主流程 ───────────────────────────────────────────────────

def enable_utf8_output():
    """Windows 控制台常为 GBK，强制 UTF-8 输出并容错，避免 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    enable_utf8_output()
    parser = argparse.ArgumentParser(description="数据来源自检（westock 优先）")
    parser.add_argument("--json", action="store_true", help="纯 JSON 输出")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细进度")
    args = parser.parse_args()

    if args.verbose and not args.json:
        print("[*] 正在自检数据来源...\n")

    westock = check_westock()
    if args.verbose and not args.json:
        mark = "[OK]" if westock["status"] == "available" else "[--]"
        print(f"  {mark} westock 主源: {westock['status']} ({westock.get('latency_ms', '?')}ms)")
        print(f"      {westock.get('version_raw') or westock.get('error')}")
        if westock.get("status") == "available" and not westock.get("version_match"):
            print(f"      [!] 版本不是预期的 {EXPECTED_WESTOCK_VERSION}")

    gaps = {}
    for ep in GAP_ENDPOINTS:
        entry = check_gap(ep)
        gaps[ep["key"]] = entry
        if args.verbose and not args.json:
            mark = "[OK]" if entry["status"] == "available" else "[--]"
            print(f"  {mark} {entry['label']}: {entry['status']} ({entry['latency_ms']}ms)")
            if entry.get("error"):
                print(f"      {entry['error']}")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "westock": westock,
        "gap_endpoints": gaps,
        "summary": {
            "primary_source_ok": westock["status"] == "available",
            "version_match": bool(westock.get("version_match")),
            "gaps_available": sum(1 for v in gaps.values() if v["status"] == "available"),
            "gaps_total": len(gaps),
        },
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print()
        s = report["summary"]
        if s["primary_source_ok"]:
            print("[OK] 主源 westock 可用"
                  + ("（版本匹配）" if s["version_match"] else "，但版本与预期不符"))
            print(f"   缺口端点：{s['gaps_available']}/{s['gaps_total']} 可用")
            if s["gaps_available"] < s["gaps_total"]:
                print("   -> 缺口端点不可用时，按数据来源铁律 规则三 标注"
                      "\"数据不可得\"并记 0 分")
        else:
            print("[!!] 主源 westock 不可用 -- 无法进行分析")
            print(f"   {westock.get('error')}")

    return 0 if report["summary"]["primary_source_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
