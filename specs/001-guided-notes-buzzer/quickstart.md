# 本機啟動與驗收指南

從專案根目錄執行下列指令。

## 環境

- Python 3.13 與 PowerShell。
- 在 Google Cloud 啟用 Google Sheets API 與 Google Drive API。將測試試算表分享給服務帳戶並授予編輯權。
- 以安全方式提供 `BUZZER_TEACHER_PASSWORD`、`BUZZER_SECRET_KEY`，以及 `BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON` 或下述短效權杖。機敏值只透過環境變數傳入，不顯示於命令輸出、版本庫、範例或日誌。

## 組織禁止建立服務帳戶金鑰時

維持組織政策，請管理員在服務帳戶所在的專案啟用 **IAM Service Account Credentials API**
（`iamcredentials.googleapis.com`），並在該服務帳戶上授予你的 Google 帳號
**Service Account Token Creator**（`roles/iam.serviceAccountTokenCreator`）。
兩份測試表仍須分享給服務帳戶並授予編輯權。

安裝 Google Cloud CLI 後，在用來啟動 Flask 的 PowerShell 視窗執行以下指令。
用管理員已授權的 Google 帳號登入。輸入的是服務帳戶電子郵件。

```powershell
gcloud.cmd auth login
if ($LASTEXITCODE -ne 0) { throw 'Google Cloud 登入失敗。' }

$serviceAccount = Read-Host '輸入服務帳戶電子郵件'
$requestBody = @{
    scope = @(
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    )
    lifetime = '3600s'
} | ConvertTo-Json

try {
    $env:BUZZER_IAM_SOURCE_TOKEN = gcloud.cmd auth print-access-token
    if ($LASTEXITCODE -ne 0 -or -not $env:BUZZER_IAM_SOURCE_TOKEN) {
        throw '無法取得目前 Google 帳號的權杖。'
    }
    $env:BUZZER_GOOGLE_ACCESS_TOKEN = (Invoke-RestMethod -Method Post -ErrorAction Stop `
        -Uri "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${serviceAccount}:generateAccessToken" `
        -Headers @{ Authorization = "Bearer $env:BUZZER_IAM_SOURCE_TOKEN" } `
        -ContentType 'application/json' -Body $requestBody).accessToken
} finally {
    Remove-Item Env:BUZZER_IAM_SOURCE_TOKEN -ErrorAction SilentlyContinue
}
```

`BUZZER_GOOGLE_ACCESS_TOKEN` 優先於服務帳戶 JSON；上面範例申請的是 3,600 秒權杖，系統不會自動延長或更新它。
若過期，停止 Flask，重新執行取權杖的區塊，再從同一個 PowerShell 視窗啟動。

[Google 短效憑證指引](https://docs.cloud.google.com/iam/docs/create-short-lived-credentials-direct) · [產生權杖 API](https://docs.cloud.google.com/iam/docs/reference/credentials/rest/v1/projects.serviceAccounts/generateAccessToken)

## 安裝與啟動

```powershell
if (-not (Test-Path -LiteralPath .venv)) {
    python -c "import sys; sys.exit(sys.version_info[:2] != (3, 13))"
    if ($LASTEXITCODE -ne 0) { throw '請先選用 Python 3.13。' }
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw '虛擬環境建立失敗。' }
}
.\.venv\Scripts\python.exe -c "import sys; print(sys.version.split()[0]); sys.exit(sys.version_info[:2] != (3, 13))"
if ($LASTEXITCODE -ne 0) { throw '既有 .venv 需要用 Python 3.13 重新建立。' }
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app buzzer run --host 127.0.0.1
```

完整測試須全數通過。自動測試用暫存資料庫及 Sheets 替身。

既有 `.venv` 若顯示其他 Python 版本，請先移開舊目錄，再用 Python 3.13 執行檔建立新的 `.venv`。
在原目錄直接重建可能留下舊版的二進位套件，造成 `_cffi_backend` 載入失敗。

啟動後，老師開啟 `http://127.0.0.1:5000/teacher`，學生開啟 `http://127.0.0.1:5000/`。
用不同瀏覽器設定檔或獨立工作階段模擬不同組別。

若本機已安裝 Google Chrome，可另跑瀏覽器測試。

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py
```

## 人工驗收

1. 老師登入 /teacher，輸入活動名稱及 Google Sheets 連結，讀取分頁並預覽。核對題號／題目／答案格；取消不建立活動，確認才建立。
2. 批次或逐組建立至少兩組。複製活動專屬網址，提供活動識別碼給學生。
3. 用隔離瀏覽器模擬不同組，輸入活動碼、讀取及選組加入；不需組別加入碼。同組另一工作階段應同步答案。
4. 老師開放全部題目；學生提交後為已作答、有答案預覽及修改入口。相同答案重送提示未變更，修改才更新時間與順位。
5. 重新選組後原組答案保留；另一分頁舊草稿不可送到新組，會被清除並提示。
6. 老師結束，第一名直接成功；學生只見成功組名及本組答案／名次。closed 不可重開、換表或修改組別。
7. 預覽回填檢查表、格位、原值、搶答成功答案；取消不寫、確認才寫。以不同版面副本再測，核對題號、小題標示與公式未被覆蓋。
8. 下一份表另建活動；重新整理保存網址或重啟仍能讀到舊結果。實際紀錄見 [驗收清單](checklists/requirements.md)。

## 圖表驗證

用章程的 PlantUML 命令生成 PNG。實作完成後，逐項對照組件責任、類別關係及時序條件，記錄差異與修正結果，再附上測試指令和各改動的 Git commit。
