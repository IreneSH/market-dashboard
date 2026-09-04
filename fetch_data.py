"""
市場指數漲跌幅 — 每日資料更新腳本
從 Yahoo Finance 抓取各指數最近一個收盤價，計算 5 日 / 1 個月 / YTD 報酬，
輸出 data.json 供 index.html 讀取。

用法：  python fetch_data.py
輸出：  data.json（與本檔同目錄）
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# 指數設定：只需要改這裡。
#   group  : 表格分組（成熟市場 / 亞洲市場）
#   name   : 顯示名稱（沿用週報用字）
#   ticker : Yahoo Finance 代號
#   note   : 替代標的說明（顯示在表格右側小字），沒有就留空
# ---------------------------------------------------------------------------
INDEXES = [
    # ---- 成熟市場 ----
    {"group": "成熟市場", "name": "MSCI 發達市場",      "ticker": "URTH",       "note": "以 iShares MSCI World ETF (URTH) 代替"},
    {"group": "成熟市場", "name": "美國 S&P 500",       "ticker": "^GSPC",      "note": ""},
    {"group": "成熟市場", "name": "美國 道瓊工業",       "ticker": "^DJI",       "note": ""},
    {"group": "成熟市場", "name": "歐洲 STOXX 600",     "ticker": "^STOXX",     "note": ""},
    {"group": "成熟市場", "name": "美國 Nasdaq 100",    "ticker": "^NDX",       "note": ""},
    {"group": "成熟市場", "name": "日本 TOPIX",         "ticker": "1306.T",     "note": "以 NEXT FUNDS TOPIX ETF (1306.T) 代替"},
    {"group": "成熟市場", "name": "日本 日經 225",       "ticker": "^N225",      "note": ""},
    {"group": "成熟市場", "name": "美國 費城半導體",     "ticker": "^SOX",       "note": ""},
    # ---- 亞洲市場 ----
    {"group": "亞洲市場", "name": "香港 恒生指數",       "ticker": "^HSI",       "note": ""},
    {"group": "亞洲市場", "name": "越南 VN-Index",      "ticker": "VNM",        "note": "以 VanEck Vietnam ETF (VNM, 美元計價) 代替"},
    {"group": "亞洲市場", "name": "印度 Nifty 50",      "ticker": "^NSEI",      "note": ""},
    {"group": "亞洲市場", "name": "MSCI 亞洲（日本除外）","ticker": "AAXJ",       "note": "以 iShares MSCI All Country Asia ex Japan ETF (AAXJ) 代替"},
    {"group": "亞洲市場", "name": "澳洲 ASX 200",       "ticker": "^AXJO",      "note": ""},
    {"group": "亞洲市場", "name": "印度 BSE 500",       "ticker": "BSE-500.BO", "note": "代替 Nifty MidSmall 400"},
    {"group": "亞洲市場", "name": "馬來西亞 KLCI",      "ticker": "^KLSE",      "note": ""},
    {"group": "亞洲市場", "name": "新加坡 STI",         "ticker": "^STI",       "note": ""},
    {"group": "亞洲市場", "name": "印尼 JCI",           "ticker": "^JKSE",      "note": ""},
    {"group": "亞洲市場", "name": "中國 上証綜指",       "ticker": "000001.SS",  "note": ""},
    {"group": "亞洲市場", "name": "菲律賓 PSEi",        "ticker": "PSEI.PS",    "note": ""},
    {"group": "亞洲市場", "name": "泰國 SET", "ticker": "THD", "note": "以 iShares MSCI Thailand ETF (THD, 美元計價) 代替"},
    {"group": "亞洲市場", "name": "台灣 加權指數 TAIEX", "ticker": "^TWII",      "note": ""},
    {"group": "亞洲市場", "name": "中國 滬深 300", "ticker": "510300.SS", "note": "以華泰柏瑞滬深300 ETF (510300.SS) 代替"},
    {"group": "亞洲市場", "name": "韓國 KOSPI",         "ticker": "^KS11",      "note": ""},
]

GROUP_ORDER = ["成熟市場", "亞洲市場"]


def pct(now: float, base: float):
    if base is None or base == 0 or pd.isna(base) or pd.isna(now):
        return None
    return round((now / base - 1) * 100, 2)


def close_on_or_before(s: pd.Series, d: date):
    """取 d 當日或之前最近一個交易日的收盤價（處理各市場休市日不同）。"""
    sub = s[s.index.date <= d]
    return None if sub.empty else float(sub.iloc[-1])


def compute(ticker: str, hist: pd.DataFrame):
    if hist is None or hist.empty or "Close" not in hist:
        return None
    s = hist["Close"].dropna()
    if s.empty:
        return None
    # 只取「昨日以前」已完成的交易日，避免抓到盤中價
    today_utc = datetime.now(timezone.utc).date()
    s = s[s.index.date < today_utc]
    if s.empty:
        return None

    last_dt = s.index[-1].date()
    last = float(s.iloc[-1])

    # 5 日報酬：往前推 5 個該市場的交易日
    base_5d = float(s.iloc[-6]) if len(s) >= 6 else None
    # 1 個月報酬：一個月前（同日）或之前最近一個交易日
    base_1m = close_on_or_before(s, (pd.Timestamp(last_dt) - pd.DateOffset(months=1)).date())
    # YTD：去年最後一個交易日
    base_ytd = close_on_or_before(s, date(last_dt.year - 1, 12, 31))

    return {
        "close": round(last, 2),
        "date": last_dt.isoformat(),
        "r5d": pct(last, base_5d),
        "r1m": pct(last, base_1m),
        "rytd": pct(last, base_ytd),
    }


def main():
    start = date(date.today().year - 1, 12, 1)  # 足以涵蓋去年底收盤
    tickers = [i["ticker"] for i in INDEXES]

    print(f"Downloading {len(tickers)} tickers from {start} ...")
    raw = yf.download(
        tickers, start=start.isoformat(), group_by="ticker",
        auto_adjust=False, threads=True, progress=False,
    )

    rows, failed = [], []
    for item in INDEXES:
        t = item["ticker"]
        try:
            hist = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            res = compute(t, hist)
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] {t}: {e}", file=sys.stderr)
            res = None
        if res is None:
            failed.append(t)
            res = {"close": None, "date": None, "r5d": None, "r1m": None, "rytd": None}
        rows.append({**item, **res})

    # 各分組依 5 日報酬由高到低排序（無資料者排最後）
    def sort_key(r):
        return (r["r5d"] is None, -(r["r5d"] or 0))

    groups = []
    for g in GROUP_ORDER:
        members = sorted([r for r in rows if r["group"] == g], key=sort_key)
        groups.append({"name": g, "rows": members})

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Yahoo Finance (yfinance)",
        "groups": groups,
        "failed": failed,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote data.json — {len(rows) - len(failed)}/{len(rows)} ok")
    if failed:
        print("Failed tickers:", ", ".join(failed))


if __name__ == "__main__":
    main()
