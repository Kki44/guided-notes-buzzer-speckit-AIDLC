# Guided Notes 課堂搶答系統

老師預覽並確認 Google Sheets 學習單後建立分組活動，一次開放所有題目。學生自由選題提交或修改；結束後每題第一名取得搶答成功資格，老師可預覽並確認寫回原表答案格。

使用 **SpecKit／AIDLC＋PlantUML Design First**。公開版包含程式、測試、需求規格及 PlantUML 圖表。

## 1. 核心功能

| 功能 | 老師 | 學生 |
| --- | --- | --- |
| 匯入 | 讀取分頁、預覽題號／題目／答案格，確認建立活動 | 查看已保存題目 |
| 組別 | 逐組建立或輸入 1–100 組批次產生，準備階段可刪組 | 輸入活動識別碼選組，不需加入碼 |
| 搶答 | 至少兩組、一次開放／結束全部題目 | 已加入組員可選題提交、修改 |
| 同步 | 查看各組最後答案與台灣提交時間 | 已作答卡、答案預覽、修改入口，同組同步 |
| 重新選組 | 不需審核 | 只移動本人，原組答案保留；舊分頁版本拒絕 |
| 結果 | 完整順位、第一名成功 | 本組答案／名次、成功組名，不看其他組答案 |
| 原表回填 | 預覽目標格與答案，確認後才寫入 | 無寫回權限 |
| 刪除活動 | 確認後永久刪除本機活動與相關資料，Google Sheets 保留 | 無刪除權限 |
| 活動恢復 | 活動清單、複製活動專屬網址 | 依入組權限讀取該活動 |

活動只允許 **準備 → 開放 → 結束**。closed 不重開、不換表；下一份表另建活動。沒有正誤按鈕、遞補或正確答案公開，搶答成功不代表答案正確。舊活動與退役資料保留，老師可確認刪除準備中或已結束活動；開放中及回填待核對時禁止刪除。Google Sheets 已寫入內容不受影響。

這版加入匯入與回填預覽、批次建立組別、活動專屬網址與直接重新選組。舊輪次查閱入口已移除，已結束活動仍可透過活動清單或專屬網址查看結果。老師可在「活動」面板選擇要清理的活動，按「刪除活動」後確認。取消確認會保留資料。測試不同班級時，可從空白學習單範本複製一份，分享給服務帳戶並授予編輯權，再建立新活動。

## 2. 排名、修改與隱私

1. 同組同題只保留最後有效答案，去除首尾空白後不得空白、最多 4,000 字。
2. 實際修改會重新計時；相同答案再送出提示「答案未變更，無須重新提交」，不更新時間及序號。
3. 網路重試沿用成功 receipt，回原結果且不重計；不同內容使用相同 receipt 會被拒絕。
4. 每題依最後有效 **資料庫接收序號** 升冪排名；伺服器時間僅作顯示，時鐘倒退不反轉順位。
5. 第一名直接取得搶答成功資格，無人提交則無成功組別；不判對錯、不遞補。
6. 活動中學生只看本組資料，結束後僅增加成功組名及本組名次。成功組答案不向其他組公開。

同瀏覽器一般分頁共用身分；重新選組會影響該瀏覽器在本場的分頁，其他分頁同步後清除草稿並提示確認。模擬不同組請用不同瀏覽器設定檔或隔離工作階段。

## 3. AIDLC 文件與圖表

| 階段 | 文件 |
| --- | --- |
| Constitution | [章程](.specify/memory/constitution.md) |
| Specify／Clarify | [SRS](specs/001-guided-notes-buzzer/spec.md) |
| Plan | [SDS](specs/001-guided-notes-buzzer/plan.md)、[LLD](specs/001-guided-notes-buzzer/lld.md)、[資料模型](specs/001-guided-notes-buzzer/data-model.md) |
| Tasks／Implement | [任務拆分](specs/001-guided-notes-buzzer/tasks.md)、[核心調整](docs/superpowers/plans/2026-11-26-core-alignment.md)、[刪除活動](docs/superpowers/plans/2026-11-26-delete-activity.md) |
| 契約 | [Web API](specs/001-guided-notes-buzzer/contracts/web.md)、[Sheets](specs/001-guided-notes-buzzer/contracts/sheets.md) |
| 驗證 | [需求追蹤](specs/001-guided-notes-buzzer/traceability.md)、[紀錄](specs/001-guided-notes-buzzer/validation.md)、[人工清單](specs/001-guided-notes-buzzer/checklists/requirements.md) |
| 索引／操作 | [架構索引](specs/001-guided-notes-buzzer/architecture.md)、[啟動指南](specs/001-guided-notes-buzzer/quickstart.md) |

圖表： [組件](diagrams/component.png)、[類別](diagrams/class.png)、[總時序](diagrams/sequence.png)、[匯入](diagrams/sequence-import.png)、[提交](diagrams/sequence-submission.png)、[回填](diagrams/sequence-export.png)、[直接換組](diagrams/sequence-transfer.png)、[狀態](diagrams/activity-state.png)、[AIDLC](diagrams/aidlc-process.png)。

每張 PNG 的 `.puml` 同目錄保存。Specify 先更新圖表，Plan 以圖表為藍圖，實作完成後對照組件責任、資料欄位與互動順序。執行：

```powershell
java -jar plantuml.jar -charset UTF-8 -failfast2 "./diagrams/*.puml"
java -jar plantuml.jar -charset UTF-8 -checkonly "./diagrams/*.puml"
```

## 4. 技術與結構

Python 3.13／Flask 3、Jinja、原生 JavaScript／CSS、SQLite WAL、google-auth／requests；pytest 與 Playwright。單程序約每秒輪詢，預設只監聽本機 127.0.0.1，不需部署雲端主機。

```text
buzzer/        權限、活動、預覽簽章、提交結算、Google 格位與回填
static/        老師／學生腳本與樣式
templates/     獨立老師及學生頁面
tests/         正常、邊界、並行、權限及瀏覽器驗證
diagrams/      PlantUML 與 PNG
specs/         SRS、SDS、LLD、契約、任務與追蹤
instance/      本機活動資料庫（Git 忽略）
```

## 5. 取得原始碼與安裝

需要 Git、Python 3.13；本節命令使用 Windows PowerShell。可直接從公開儲存庫下載原始碼。

```powershell
git clone https://github.com/Kki44/guided-notes-buzzer-speckit-AIDLC.git
Set-Location '.\guided-notes-buzzer-speckit-AIDLC'

py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```

已在既有專案目錄工作時，不需再次 clone；先切到該專案根目錄。若沒有 `py` 啟動器，可用確認為 Python 3.13 的 `python` 執行 `python -m venv .venv`。既有虛擬環境若是其他版本，不要直接混用套件。

自動測試會建立隔離資料庫與試算表測試替身，不需要真實 Google 憑證，也不會寫入你的學習單。

## 6. 環境變數與機敏資料

| 環境變數 | 必要性 | 用途 |
| --- | --- | --- |
| `BUZZER_TEACHER_PASSWORD` | 啟動必填 | 老師管理台密碼 |
| `BUZZER_SECRET_KEY` | 啟動必填 | Cookie 與預覽確認簽章 |
| `BUZZER_GOOGLE_ACCESS_TOKEN` | 真實 Google 操作時擇一 | 短效存取權杖，存在時優先使用 |
| `BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON` | 真實 Google 操作時擇一 | 服務帳戶 JSON 的完整內容，不是檔案路徑 |

不要把密碼、權杖、金鑰或完整憑證貼進原始碼、README、Git commit、截圖或日誌。應用程式以環境變數讀取機敏值，不依賴儲存庫中的憑證檔，也沒有自動載入 `.env` 的流程。

以下在**準備啟動 Flask 的同一個 PowerShell**設定管理密碼、首次簽章金鑰與短效權杖；輸入時不顯示文字，也不將實際值寫入命令歷史：

```powershell
$teacherInput = Read-Host '輸入老師管理密碼' -AsSecureString
$env:BUZZER_TEACHER_PASSWORD = [System.Net.NetworkCredential]::new('', $teacherInput).Password

if (-not $env:BUZZER_SECRET_KEY) {
    $env:BUZZER_SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
    if ($LASTEXITCODE -ne 0) { throw '無法產生簽章金鑰。' }
}

$tokenInput = Read-Host '貼上 Google 短效存取權杖' -AsSecureString
$env:BUZZER_GOOGLE_ACCESS_TOKEN = [System.Net.NetworkCredential]::new('', $tokenInput).Password
Remove-Variable teacherInput, tokenInput
```

權杖取得方式見下一節。若改用服務帳戶 JSON，須由安全來源提供完整 JSON 至對應環境變數；不使用短效權杖時，從目前 PowerShell 移除 `BUZZER_GOOGLE_ACCESS_TOKEN`，以免它優先覆蓋 JSON 模式。

```powershell
# 僅在改用已設定的服務帳戶 JSON 模式時執行
Remove-Item Env:BUZZER_GOOGLE_ACCESS_TOKEN -ErrorAction SilentlyContinue
```

僅檢查設定是否存在，不印出內容：

```powershell
[pscustomobject]@{
    TeacherPasswordLoaded = -not [string]::IsNullOrWhiteSpace($env:BUZZER_TEACHER_PASSWORD)
    SecretKeyLoaded = -not [string]::IsNullOrWhiteSpace($env:BUZZER_SECRET_KEY)
    GoogleTokenLoaded = -not [string]::IsNullOrWhiteSpace($env:BUZZER_GOOGLE_ACCESS_TOKEN)
    GoogleJsonLoaded = -not [string]::IsNullOrWhiteSpace($env:BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON)
}
```

PowerShell 的這些設定供目前程序及子程序使用，關閉視窗後不會自動在新視窗恢復。若要延續原有登入與預覽，重新啟動時須從安全來源提供**相同的** `BUZZER_SECRET_KEY`；更換它會讓舊 Cookie 與尚未確認的預覽失效。不要為了方便而把實際值寫進啟動腳本或提交儲存庫。

## 7. Google Sheets 授權與學習單

1. 準備原生 Google 試算表；若檔案仍以 `.xlsx` 型別開在雲端硬碟，先另存為 Google 試算表，再使用新連結。
2. 在 Google Cloud 專案啟用 Google Sheets API 與 Google Drive API。
3. 使用服務帳戶作為讀寫身分，將測試試算表分享給該服務帳戶電子郵件，授予編輯權。
4. 使用該服務帳戶憑證或以該身分取得的短效權杖，設定上一節對應環境變數。
5. 若組織禁止建立服務帳戶金鑰，可依 [無金鑰短效權杖流程](specs/001-guided-notes-buzzer/quickstart.md) 使用 IAM Service Account Credentials API 與管理員授予的 Service Account Token Creator 權限，不需要關閉組織限制。

短效權杖不會由本應用自動續期。到期後重新取得權杖，更新環境，再重啟 Flask；不需要重建活動。若 PowerShell 阻擋 `gcloud.ps1`，可使用 `gcloud.cmd` 執行同一組 CLI 命令。

原版學習單以唯一「題號／題目／作答」表頭及合併格定位答案。合併主題下的小題會變成 Q1.1、Q1.2 等，分別提交與結算。亦相容成對的 Qn／{{Qn}} 標記。系統保存實際原格與錨點，不把第幾題寫死在某個儲存格。

建議以未填答案的副本驗收。多張工作表時先「讀取工作表」，再選擇正確工作表；只有一張時可自動選取。

## 8. 啟動與重新啟動

確認在專案根目錄，且同一 PowerShell 已載入必要環境變數：

```powershell
.\.venv\Scripts\python.exe -m flask --app buzzer run --host 127.0.0.1
```

- 老師管理台：<http://127.0.0.1:5000/teacher>
- 學生作答頁：<http://127.0.0.1:5000/>

Flask 會持續佔用該 PowerShell，這是正常執行狀態。停止請按 **Ctrl+C**。更新程式或權杖後，從同一視窗重新執行啟動指令；頁面按 **Ctrl+F5** 載入新腳本。

不要同時啟動兩個服務程序來操作同一份活動資料；接收序列與回填鎖是程序內共用狀態。

## 9. 完整操作流程

1. 老師登入 `/teacher`，選「建立新活動」，輸入活動名稱與 Google Sheets 連結。
2. 按「讀取工作表」、選分頁、按「預覽題目」。檢查題號、題目與答案格，再按「確認匯入並建立活動」。取消不會建立活動。預覽 20 分鐘過期，來源變更需重新預覽。
3. 批次建立至少兩組或逐組命名建立。曾有學生加入後即不能整批重建，即使刪除該組也不解除。複製活動專屬網址留存，將畫面上的活動識別碼給學生。
4. 學生進入 `/`，輸入活動識別碼、讀取活動、選組加入。學生不需管理密碼或組別加入碼。
5. 老師開放全部題目。學生按題卡作答；送出後可看到已作答、上一次答案與修改按鈕，同組組員同步。相同答案不重新計時。
6. 選錯組可重新選組；原組答案保留。其他分頁舊草稿不得誤送到新組。
7. 老師結束，全題唯讀；每題第一名直接成功，學生只能看成功組名及本組答案／名次。
8. 老師按「預覽回填 Google Sheets」，檢查目標表、格位、原值與搶答成功答案。答案未經正確性判定；按取消不寫，按確認才重驗原格並批次寫入。原題／保護／內容衝突則整批停止。
9. 下一份學習單選「建立新活動」重做匯入。舊活動仍可用清單或專屬網址查看，不會因建立下一場而被覆蓋。

## 10. 自動測試

```powershell
Set-Location 'D:\SWE proj'
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py
```

瀏覽器測試需另以 `.\.venv\Scripts\python.exe -m pip install playwright` 安裝 Playwright，並在本機安裝 Google Chrome。browser_smoke 檔名不在預設 pytest 掃描規則，需另外執行第二條。測試用隔離 SQLite 及 Google 替身，不讀寫真實學習單。涵蓋多組並行、同組同步、截止、版本、預覽取消／確認、原格衝突、未知結果、重啟、手機與桌面流程；結果記於驗證文件。

## 11. 人工驗收

依 [人工驗收清單](specs/001-guided-notes-buzzer/checklists/requirements.md) 使用兩份不同位置的 Google Sheets 副本實測。記錄驗證人、日期、活動識別碼、預期／實際結果與去敏截圖。確認真實權限、API 授權、題號與小題標示保留、答案只寫正確格位。自動驗證不等於已由真人驗收。

## 12. 常見問題

- Google 驗證失敗：短效權杖可能到期，從安全方式更新環境後重啟，不需重建活動。
- 權限拒絕：確認已啟用 Sheets／Drive、檔案為原生試算表，並分享給目前服務身分且授予編輯權。
- 預覽失效：過了 20 分鐘、工作階段或來源內容變更時，重新預覽再確認；不要略過檢查直接覆蓋。
- `_cffi_backend` 錯誤：確認 .venv 為 Python 3.13，避免混用其他 Python 的二進位套件；重新安裝開發需求。
- 另一個分頁組別改變：一般分頁共用工作階段，請確認組別後重新輸入；測不同學生用隔離工作階段。
- 沒有正確答案／審查按鈕：目前只判定搶答資格，不判正確性；老師可人工查看再決定是否確認回填。
- 結束後不能重開：這是核定流程。下一份表另建活動，舊資料保存不被替換。

## 13. 資料與 Git

資料庫、收據與待確認回填保存在本機 instance，clone 不帶入課堂資料或憑證。升級只新增 import_key／joined_once／索引／持久序號，保留既有表與舊判定／申請／輪次資料。停止使用的欄位不再決定新流程結果。舊輪次僅作資料相容留存，不提供面板或查閱 API。

.gitignore 排除環境、資料庫、快取與日誌；私人儲存庫也不能提交機密。每次變更更新規格／圖表及相關測試，驗證後建立 commit。Git 日期是提交日期，不代表剛推送的時間，無須重寫歷史。
