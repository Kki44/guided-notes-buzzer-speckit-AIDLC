# 核心功能驗證紀錄

## 2026-11-26 恢復老師刪除活動

- 老師確認後可刪除 ready／closed 活動及本機相關資料；open、待核對回填、非老師、CSRF 不符、未確認皆拒絕。Google Sheets 不寫入、不刪除。
- 先重現測試失敗後實作；新增本機關聯清理、其他活動保留及確認邊界回歸。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：95 passed in 10.41s。
- `.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-delete-activity`：2 passed in 40.16s，包含刪除取消／確認及成功返回新活動。
- 文件一致性：5 passed；PlantUML 9 圖已重新產生。測試使用隔離資料庫及 FakeSheets，未刪除實際課堂資料。

## 2026-11-26 v3.0.1 移除舊輪次功能

- 保留活動專屬網址及既有活動恢復；移除舊輪次面板、前端 fetch／渲染、相關樣式及 GET history 路由。舊 round_history 資料只作相容留存，不刪除資料列，也不再提供查閱 API。
- 先修改正常及舊資料邊界測試，重現 2 failed（面板仍存在、API 仍回 200）；移除實作後確認舊資料列仍完整。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：**93 passed in 9.59s**。
- `.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-remove-rounds`：**2 passed in 32.29s**；同時確認舊輪次控制項不存在、活動專屬網址恢復及回填流程正常。
- PlantUML CLI 重新產生全部 9 張 PNG，類別及組件圖標示退役資料僅相容留存，無舊輪次功能入口。README、規格與 API 文件已同步。
- 本次未呼叫真實 Google 寫入；驗證使用隔離資料庫及 FakeSheets。

## 2026-11-26 v3.0 核心流程調整

- 已核定並實作：匯入預覽確認建立活動、單向活動狀態、交易內有效序號、同答案拒絕、固定第一名、學生僅本組答案與得主組名、直接重新選組、批次組別、活動網址及回填預覽確認。保留所有既有業務資料，退役操作不可再寫入。
- 基準測試：75 passed；新規則紅燈確認未支援的行為後實作，相關舊測試按新需求更新，未以停用測試迴避變更。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：**92 passed in 9.49s**。含正常及邊界、來源變更／跨工作階段／過期預覽、相同答案並行、時鐘倒退、八組同步、截止競爭、原格保護、回填不明結果、重啟及舊 schema 升級。
- `.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-alignment-final`：**2 passed in 30.91s**。真實 Chrome、隔離資料庫及 FakeSheets；涵蓋輸入改變時拒絕遲到的預覽、取消／確認匯入、批次及刪組、同組分頁、已作答與修改、排序與公開範圍、取消／確認寫回、專屬網址恢復、下一場獨立、換組舊草稿拒絕與手機不溢出。
- README 7 段 PowerShell 程式碼只做語法解析：0 errors，未執行真實憑證設定。
- PlantUML CLI `-charset UTF-8 -failfast2 "./diagrams/*.puml"`：9 張 PNG 成功產生；類別圖含實際 12 表及新增 import_key／joined_once，圖碼表欄位由文件測試核對。主要時序與最終路由／原格回填流程已對照。
- 獨立程式審查：修復刪除已加入組別後可繞過整批重建鎖的問題；新增永久 joined_once 及回歸測試，複查無重大問題。
- 真實 Google API 權限、分享與雲端寫回**未在本次自動測試執行**；須依人工清單另行實測。以下紀錄為歷史版本驗證，不代表舊功能仍屬現行規格。

## 2026-11-26 儲存庫 README 與啟動文件

- 根目錄新增 [README](../../README.md)，包含功能規則、AIDLC 文件與圖表索引、安裝、環境變數、Google Sheets 授權、啟動／重啟、操作流程、測試、人工驗收與常見問題。
- 文件連結測試加入根目錄 README；先重現缺少檔案的失敗，再建立文件確認連結可解析。修正啟動指南對學生公開得主名稱的舊描述，與目前角色視圖一致。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：75 passed。
- 以 PowerShell Parser 對 README 的 8 段 PowerShell 程式碼做語法解析，全部通過；不執行真實憑證輸入、Google 操作或新增環境設定。
- `.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py`：2 passed；使用隔離資料庫與 Sheets 替身執行既有課堂、換表及換組流程。

## 2026-11-20 v2.0.2 核心需求完成狀態

- 結果輸出依 Google Sheets 同步與回填定義；未採用的功能不列為需求、待辦或實作缺項。核心功能實作狀態與人工驗收證據分開記錄。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short tests/test_architecture_docs.py`：5 passed。新增需求範圍檢查，確認核心完成狀態不混入未採用功能。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：75 passed。應用功能、API 與圖表時序未變更。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-core-scope-browser tests/browser_smoke.py`：2 passed；使用模擬 Sheets 執行課堂、換表與換組流程。

## 2026-11-20 v2.0.1 獨立規格文件

- 規格、設計、圖表、追蹤與審核清單僅依使用者已確認需求、章程及目前程式；維持原有功能與 API 行為。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short tests/test_architecture_docs.py`：4 passed。新增來源獨立性檢查，並保留文件連結、PNG 與實際資料表／欄位對照檢查。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：74 passed。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-independent-specs-browser tests/browser_smoke.py`：2 passed，沿用模擬 Sheets 驗證課堂、換表與換組流程。
- PlantUML CLI 使用 `-charset UTF-8 -failfast2 "./diagrams/*.puml"` 重新產生全部 9 份 PNG，並以 `-charset UTF-8 -checkonly "./diagrams/*.puml"` 檢查，退出碼均為 0；已查看更新後的總時序與 AIDLC 流程圖。

## 2026-11-20 AIDLC v2.0 現況文件包

**行為基準**：Git `a447f88`。本次不修改應用功能，更新 SRS／SDS／LLD／資料模型／需求追蹤與 9 份 PlantUML 藍圖。審核入口為 [architecture.md](architecture.md)。

| 本次檢查 | 證據與結果 |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q --tb=short` | 73 passed，含新增文件鏈結、PNG 產物、資料類別與實際 SQLite 表對照測試。 |
| `.\.venv\Scripts\python.exe -m pytest -q --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-aidlc-docs-browser tests/browser_smoke.py` | 2 passed；既有課堂、換表、進度、換組流程通過，使用模擬 Sheets。 |
| PlantUML CLI | 使用可攜 Java 與 plantuml.jar，命令參數 `-charset UTF-8 -failfast2 "./diagrams/*.puml"`：9 份來源全部成功輸出同目錄 PNG，退出碼 0；另以 `-charset UTF-8 -checkonly "./diagrams/*.puml"` 通過語法檢查，退出碼 0。 |
| 圖碼人工核對 | 組件責任對應 routes／access／EventOrder／submissions／review／guided_notes／GoogleSheets／Store；類別圖含 12 張實體表及遷移欄位，時序含換表雙檢、收據先後、關閉序列、回填中斷與換組版本。 |
| 視覺檢查 | 查看架構、資料類別、活動狀態、提交、回填、換組及流程 PNG；調整複合主鍵顯示與 AIDLC 驗證失敗重試回圈。 |
| 核心實作缺項 | 依目前已確認需求及自動化證據，未列出核心功能的實作缺項；驗收發現缺陷時另行記錄。 |
| 人工驗收待辦 | 使用者核准本文件、使用真實 Google 工作表完成核心流程並留存紀錄。此為驗收證據狀態，不列為功能尚未實作。 |

此份為本系統的現況重建，依據已確認需求與實際程式，不補造過去所有階段的執行證明。

## 早期核心版本的歷史驗證

| 檢查 | 實際結果 |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q` | 35 個測試通過，包含原版範本辨識、空白還原、重複題號、跨組隔離、提交與關閉排序、審查更正、原格衝突、回填批次及重啟核對。 |
| 教授提供的兩份原版 XLSX | 以附件原始儲存格值與合併資料執行匯入解析器。單題、題組各正確辨識 6 個答案格，沒有修改附件。 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py` | Chrome／Playwright 以一個老師及兩組學生的獨立瀏覽器工作階段跑通建立、匯入、入組、同步、提交、鎖定、遞補及回填。試算表操作使用替身。 |
| `.\.venv\Scripts\python.exe -m pip check` | 無依賴衝突。 |
| `node --check static/teacher.js`、`node --check static/student.js` | 兩份 JavaScript 語法通過。 |
| `java -jar plantuml.jar -charset UTF-8 -failfast2 "./diagrams/*.puml"` 與 `java -jar plantuml.jar -charset UTF-8 -checkonly "./diagrams/*.puml"` | 3 份 PlantUML 來源全部成功渲染與通過語法檢查。 |

## 早期圖表與程式碼對照（現況以 v2.0 文件包為準）

| 藍圖 | 核對結果 |
| --- | --- |
| [組件圖](../../diagrams/component.puml) | 老師與學生介面對應 `templates/`、`static/`，統一操作入口為 `buzzer/routes.py`。`access.py`、`activity.py`、`submissions.py`、`review.py`、`guided_notes.py` 分別負責身分、事件順序、提交、審查、匯入與回填。`store.py` 保存活動資料，`sheets.py` 介接 Drive 權限與原工作表。 |
| [類別圖](../../diagrams/class.puml) | `buzzer/store.py` 定義活動、工作表識別、組別、加入、題目、有效提交、送出識別、順位判定與回填。逐題公開結果由固定順位與可更正判定導出。補畫審查版本、題號格定位及可重啟核對的待確認回填批次。 |
| [時序圖](../../diagrams/sequence.puml) | `buzzer/routes.py` 與 `buzzer/activity.py` 共同安排提交及關閉順序，`buzzer/review.py` 在結束交易中鎖定各題順位。回填由 `buzzer/guided_notes.py` 預檢，保存待核對批次後才寫入。補畫回應中斷後重讀原格及確認結果的分支。 |

## 待驗收

- T030 與最終交付確認 T032 的真實原表專項證據仍待補齊。本次沒有進行真實 Google 操作，也未檢查或輸出機敏環境內容；依 [驗收指南](quickstart.md) 設定與授權後，須以兩份不同題數與格位的原表留存真人驗收紀錄。
- Google Sheets 的前置讀取與原子批次是兩次操作。回填期間須暫停共同編輯；若 Google 回應中斷，先核對已觀察的原值與目標值，再決定後續操作。若 Google 在逾時後仍處理原請求，當下讀取只能確認當下內容。

## 2026-11-20 學生換表同步回歸

- 重現：學生的輪詢 GET 一直沒有回應時，下一輪輪詢不會啟動，老師換表後學生持續顯示舊題目及結束狀態。
- 修正：學生讀取請求限時 8 秒，逾時顯示清楚訊息，後續輪詢重試；同步恢復後清除逾時訊息。換表同時清除隱藏表單的舊題目及草稿。
- 回歸涵蓋兩個組別、共用老師登入 Cookie 的同組視窗、保留入組、新題目與狀態同步，以及新表提交不外洩至另一組。瀏覽器以模擬 Sheets 介面執行，未操作真實 Google 工作表。
- 圖表一致性：沿用既有學生輪詢、工作表版本與匯入交易，沒有新增組件或資料結構。
- 驗證：`.\.venv\Scripts\python.exe -m pytest -q --tb=short`：59 passed；單獨執行 `tests/browser_smoke.py`（`-p no:cacheprovider --basetemp instance/pytest-sheet-sync-final`）：1 passed；`node --check static/student.js`：通過。

## 實作提交

### 2026-11-20 老師題目卡片精簡作答進度

- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：70 passed，新增教師同交易組別清單、重送不增加組數、刪組及零組別的 API 測試。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-progress-green tests/browser_smoke.py`：2 passed。新增卡片零組別、0／2、1／2、全組提交、淡綠完成標籤、未提交清單、重新開始及學生端無進度標籤檢查；既有換表與換組流程一併通過。
- `node --check static/teacher.js`、`git diff --check` 通過；PlantUML CLI 重新渲染全部三份圖表，退出碼 0。組件圖補充老師進度；類別與時序沿用原有組別、有效提交及輪詢流程，沒有新增資料表或外部依賴。
- 本次使用模擬 Sheets，未操作真實 Google 工作表。

### 2026-11-20 首次直接入組與老師審核換組

- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`：68 passed，新增 9 項換組測試（包含錯碼、無效與跨活動組別、未授權審核、作答中限制、拒絕重申、核准隔離、刪除、舊分頁及 A → B → A 組別版本）。
- `.\.venv\Scripts\python.exe -m pytest -q --tb=short --show-capture=no -p no:cacheprovider --basetemp instance/pytest-group-transfer-delivery tests/browser_smoke.py`：2 passed，包含完整課堂／換表與換組 UI 流程，以及核准後新組可作答、原組答案保留、多分頁同步及手機寬度。
- `node --check static/student.js`、`node --check static/teacher.js`：通過。PlantUML CLI 使用 `-charset UTF-8 -failfast2 "./diagrams/*.puml"` 渲染全部 3 份 PNG，退出碼 0。
- 對照圖表：入組與換組審核仍由 routes/API 入口提供；SQLite 的 transfer_requests 對應換組申請，memberships.version 對應組別版本；核准以交易更新 membership／版本／收據，輪詢顯示新組。已核對 API 身分與資料隔離，並修正程式碼審查發現的舊分頁漏帶版本重送風險。
- 本次瀏覽器測試使用模擬 Sheets，未操作真實 Google 工作表。

- `c26e354` 老師登入、活動與組別準備。
- `9b2487f` Guided Notes 匯入與學生入組。
- `be7179d` 作答同步、順位與人工審查。
- `b6b0ce1` 原格批次回填與結果核對。
