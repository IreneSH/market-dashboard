# 市場指數漲跌幅 Dashboard

複製週報「一、市場指數漲跌幅」表格，資料來源 Yahoo Finance，每日自動更新一次（抓昨日收盤）。

## 檔案
| 檔案 | 用途 |
|---|---|
| `fetch_data.py` | 從 Yahoo Finance 抓價、算 5 日 / 1 個月 / YTD 報酬，輸出 `data.json` |
| `index.html` | 靜態儀表板，讀取 `data.json` 渲染表格 |
| `.github/workflows/update.yml` | GitHub Actions 排程：每個交易日台北 06:30 自動執行並 commit `data.json` |
| `requirements.txt` | Python 套件 |

## 部署（GitHub Pages）
1. 建一個新 repo，把這些檔案全部推上去（含 `.github/` 資料夾）。
2. Repo → Settings → Actions → General → Workflow permissions 選 **Read and write permissions**（讓 Action 能 commit）。
3. Repo → Actions → 「每日更新市場指數資料」→ **Run workflow** 手動跑一次，確認 `data.json` 產生。
4. Repo → Settings → Pages → Source 選 **Deploy from a branch**，Branch 選 `main` / root。
5. 幾分鐘後網址 `https://<帳號>.github.io/<repo>/` 即可看到。

用 Netlify 也可以：把 repo 連上 Netlify，publish directory 設 `/`（根目錄），Actions 每天 commit 後 Netlify 會自動重新部署。

## 本機測試
```bash
pip install -r requirements.txt
python fetch_data.py          # 產生 data.json
python -m http.server 8000    # 瀏覽 http://localhost:8000
```
（直接雙擊 index.html 會因瀏覽器安全限制讀不到 data.json，需用 http 伺服器開啟。）

## 修改指數
只要改 `fetch_data.py` 最上方的 `INDEXES` 清單：`group`（分組）、`name`（顯示名稱）、`ticker`（Yahoo 代號）、`note`（替代說明）。排序由程式依 5 日報酬自動處理。

## 報酬計算方式
- 每個指數用自己的交易日序列，不受其他市場休市影響。
- 5 日報酬：最近收盤 ÷ 5 個交易日前收盤 − 1。
- 1 個月報酬：基期為一個月前同日；若非交易日，取之前最近一個交易日。
- YTD：基期為去年最後一個交易日收盤。
- 只採用「今日（UTC）以前」的交易日，避免抓到盤中價。
