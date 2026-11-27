# 課堂搶答核心流程調整 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. The user approved this scope and autonomous execution on 2026-11-26.

**Goal:** 將已核定的精簡核心流程落實到規格、圖表、程式及測試，保留既有資料。

**Architecture:** 沿用 Flask、SQLite、約每秒輪詢。匯入與回填先產生綁定老師工作階段、內容摘要及期限的簽章預覽，確認時重新驗證來源。資料庫交易內配置有效提交序號；活動只向前轉換。

**Tech Stack:** Python、Flask、SQLite、原生 JavaScript、pytest、Playwright、PlantUML。

**Spec:** `specs/001-guided-notes-buzzer/spec.md`（本次核定行為取代舊版）。

## Global Constraints

- 機密只能從環境變數取得，不輸出憑證或權杖。
- 每項功能有正常及邊界測試，交付前執行全套及瀏覽器測試並建立 commit。
- 不刪除既有資料；保留舊表及舊欄位，停止使用換組審核、判定及多輪新增流程。
- Specify 先更新 `diagrams/*.puml` 並以 PlantUML CLI 產生同目錄 PNG；Plan 依圖實作。

## Approved design

1. 老師讀取分頁、預覽題目及答案格，確認後才建立活動；無效、過期、不同工作階段或已變更的預覽不得建立活動。
2. ready（DRAFT）→ open → closed；至少兩組及一題、全系統最多一場 open。closed 重複關閉回原結果，不能重開或換表。
3. 保留逐組建立及準備階段刪組；增加 1–100 組批次建立。已有任何學生入組後禁止整批重建。
4. 學生輸入活動識別碼選組，首次及重新選組不需加入碼或審核。只移動本人，答案留在原組；版本遞增防止其他分頁及 A→B→A 舊送出。
5. 同組同題最後有效答案決定順位；trim 後相同答案回 409 提示、不更新提交。成功 receipt 重試仍回原結果。序號在資料庫交易內配置，不以時間排序。
6. closed 每題第一名直接取得搶答成功資格。無判對錯、遞補或正確答案欄位；學生只見得主組名及本組答案／名次。
7. 回填先預覽題號、格位、原值及目標答案並標示未判定正確性；確認重讀原格及驗證預覽摘要才寫回，取消不寫。保留整批衝突阻擋、純文字與不明結果核對。
8. 老師可複製活動專屬網址並重新讀取保存資料；保留舊輪次相容資料但不提供面板及查閱 API，不提供新增輪次、刪活動及額外進度統計。老師密碼、角色隔離與同步保留。

## Review Focus

- 跨工作階段、過期或被改動的預覽：拒絕且不寫入。
- 改組後其他分頁、A→B→A：舊版本送出不得誤寫。
- 相同答案並行、時鐘倒退、提交與截止競爭：由交易決定，序號不反轉。
- Google 回應不明、原題或答案格變動：保留待確認批次，不盲目覆蓋。
- 升級舊資料庫：舊活動、判定、歷史資料均保存，結果改以固定第一名呈現。

## Tasks

### 1. 規格與設計先行
- [x] 更新 SRS、SDS、LLD、API、資料字典、追蹤表與 PlantUML 圖。
- [x] 產生 PNG 並執行文件一致性測試。

### 2. 核心後端與預覽
- [x] 在 `tests/test_import_join.py`、`test_ranking_review.py`、`test_activity_management.py`、`test_group_transfer.py`、`test_export.py` 先建立新規則失敗測試。
- [x] `buzzer/routes.py` 加入匯入預覽／確認、批次組別、直接換組、活動網址、回填預覽／確認；移除不再提供的寫入路由。
- [x] `buzzer/review.py`、`submissions.py` 改序號排序與第一名結果；`store.py` 保留舊表，補有效序號配置。
- [x] `buzzer/guided_notes.py` 共用回填預檢，確認時檢查摘要及原格。
- [x] 更新原格、並行及權限回歸測試，執行 pytest。

### 3. 介面與端到端
- [x] `templates/teacher.html`、`static/teacher.js` 提供預覽確認、活動網址及批次組別，移除已退役操作。
- [x] `templates/student.html`、`static/student.js` 改活動碼與選組；保留卡片、預覽、修改及同步，改結果公開欄位。
- [x] `tests/browser_smoke.py` 覆蓋正常課堂、取消／確認預覽、多分頁改組、桌面與手機。

### 4. 交付
- [x] 更新 README、人工驗收及驗證紀錄；檢查圖表對照最終實作。
- [x] 執行 `.venv/Scripts/python.exe -m pytest -q --tb=short` 及 `-m pytest -q tests/browser_smoke.py`。
- [x] 建立對應 commit，回報實際指令／結果／重啟方式。

## Execution record

- 2026-11-26：使用者已接受全數建議，直接在既有工作區實作；未追蹤的工具設定不納入提交。

- 規格／主要圖表先更新並產生 PNG，再加入新規則測試；初始 9 項失敗確認缺少預覽 API，之後實作通過。
- 舊功能測試按核定規則更新，保留原格、並行、權限、八組同步及未知結果回歸。
- 瀏覽器測試重現匯入請求未回應前改欄位仍顯示舊預覽；加入請求世代識別後回歸通過。
- 獨立程式審查發現刪除已加入組別後整批重建可繞過；先重現失敗，再加 joined_once 永久標記及舊資料回補。審查確認已修復，無其他重大問題。
- 最終驗證：pytest 92 passed；Playwright 2 passed；README 7 段 PowerShell 解析錯誤 0；PlantUML 9 圖已渲染。
- Ruling: 沿用單一工作區與主分支，不改寫技術棧；使用者已授權整批功能調整與對應提交。未追蹤的工具設定與本機測試截圖不納入提交。

- 2026-11-26 後續核定：活動專屬網址保留；刪除舊輪次面板、前端載入與唯讀 API。先重現 2 項失敗後刪除對應程式，既有資料庫紀錄不刪除。文件及類別／組件圖已同步；本記錄取代先前的舊輪次唯讀查閱設計。

- 移除舊輪次的交付驗證：pytest 93 passed；Playwright 2 passed；9 張 PlantUML 重新產生，文件一致性通過。
