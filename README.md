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

## 5. 助教與新筆電的首次準備

本指南使用 Windows PowerShell。先安裝 [Python 3.13](https://www.python.org/downloads/)、[Git](https://git-scm.com/downloads) 與 [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)，安裝完成後重新開啟 PowerShell。展示使用 Chrome 與 Edge。請下載原始碼後在專案資料夾開啟終端機，家用筆電不必建立 D 槽或沿用作者的路徑。

```powershell
git clone https://github.com/Kki44/guided-notes-buzzer-speckit-AIDLC.git
Set-Location '.\guided-notes-buzzer-speckit-AIDLC'
```

也可以在 GitHub 選 Code → Download ZIP，解壓後在含有 requirements-dev.txt 的資料夾開啟 PowerShell。若已下載專案，直接進入該資料夾。虛擬環境請在新電腦重建。

### Google Cloud 與試算表的一次性準備

1. 登入 Google Cloud Console，建立或選擇有權管理的專案，記下專案 ID。
2. 在「API 和服務 → 程式庫」啟用 Google Sheets API、Google Drive API、IAM Service Account Credentials API。若 IAM API 尚未啟用也需啟用。
3. 在「IAM 與管理 → 服務帳戶」建立或選用服務帳戶，複製完整服務帳戶電子郵件。
4. 在該服務帳戶的「權限／管理存取權」新增要執行展示的 Google 帳號，授予 Service Account Token Creator（roles/iam.serviceAccountTokenCreator）。助教可以使用自行建立的服務帳戶，或由專案管理員授權助教的 Google 帳號使用指定帳戶。
5. 準備一份答案空白的原生 Google Sheets 副本。若仍顯示 .XLSX，先「檔案 → 另存為 Google 試算表」。
6. 在**副本**按「共用」，明確加入第 3 步的服務帳戶電子郵件，角色選「編輯者」，儲存後複製副本網址。每份新副本都要重新確認這個帳號的權限。

上面的 Token Creator 是「誰可以取得服務帳戶的短效權杖」，試算表共用的編輯者是「服務帳戶可以編輯哪份表」，兩者都要完成。家用筆電須用已獲授權的 Google 帳號登入。無法修改 IAM 權限時需要專案管理員處理。

此流程使用短效服務帳戶權杖，無須下載服務帳戶私鑰。預設申請 3,600 秒，較長期限需要額外組織政策。本專案不自動續期。[Google 短效憑證說明](https://docs.cloud.google.com/iam/docs/create-short-lived-credentials-direct)、[權杖 API](https://docs.cloud.google.com/iam/docs/reference/credentials/rest/v1/projects.serviceAccounts/generateAccessToken)

## 6. 從安裝到取得權杖及啟動，一次執行

完成第 5 節後，請在**專案根目錄的同一個 PowerShell**貼上以下整個區塊。依序完成 Python 檢查、安裝套件、Google 登入、輸入服務帳戶、申請新權杖、設定老師密碼及啟動。首次會開啟瀏覽器登入 Google。任一步驟失敗會停止，請先看錯誤，再重新執行整段。

<!-- unified-startup -->
```powershell
& {
    $ErrorActionPreference = 'Stop'
    if (-not (Test-Path -LiteralPath '.\requirements-dev.txt')) {
        throw '請先進入專案根目錄，該目錄應有 requirements-dev.txt。'
    }

    if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) {
        $buzzerPython = Read-Host '輸入 Python 3.13 的 python.exe 完整路徑（不加引號）'
        if (-not (Test-Path -LiteralPath $buzzerPython -PathType Leaf)) {
            throw '找不到 Python，請確認安裝位置與路徑。'
        }
        & $buzzerPython -c "import sys; sys.exit(sys.version_info[:2] != (3, 13))"
        if ($LASTEXITCODE -ne 0) { throw '請選用 Python 3.13 的執行檔。' }
        & $buzzerPython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw '建立虛擬環境失敗。' }
    }
    $buzzerPython = (Resolve-Path '.\.venv\Scripts\python.exe').Path
    & $buzzerPython -c "import sys; sys.exit(sys.version_info[:2] != (3, 13))"
    if ($LASTEXITCODE -ne 0) { throw '既有 .venv 不是 Python 3.13，請改名保留後重新建立。' }
    & $buzzerPython -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw '安裝套件失敗，請確認網路及 Python 版本。' }

    $buzzerGcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
    if ($buzzerGcloudCommand) {
        $buzzerGcloud = $buzzerGcloudCommand.Source
    } else {
        $buzzerGcloud = Read-Host '輸入 Google Cloud SDK 的 bin\gcloud.cmd 完整路徑（不加引號）'
        if (-not (Test-Path -LiteralPath $buzzerGcloud -PathType Leaf)) {
            throw '找不到 gcloud.cmd，請安裝 Google Cloud CLI 並重新開啟 PowerShell。'
        }
    }
    # BEGIN GCLOUD USER CONFIG
    $env:CLOUDSDK_CONFIG = Join-Path $env:LOCALAPPDATA 'GuidedNotesBuzzer\gcloud'
    if ((Test-Path -LiteralPath $env:CLOUDSDK_CONFIG) -and
        -not (Test-Path -LiteralPath $env:CLOUDSDK_CONFIG -PathType Container)) {
        throw 'Google CLI 設定路徑已被檔案占用，請先確認該路徑。'
    }
    [void](New-Item -ItemType Directory -Path $env:CLOUDSDK_CONFIG -Force -ErrorAction Stop)
    $buzzerProbe = Join-Path $env:CLOUDSDK_CONFIG ([Guid]::NewGuid().ToString() + '.write-test')
    try {
        [IO.File]::WriteAllText($buzzerProbe, '')
    } catch {
        throw '目前使用者無法寫入 Google CLI 設定目錄，請檢查資料夾權限。'
    } finally {
        Remove-Item -LiteralPath $buzzerProbe -ErrorAction SilentlyContinue
    }
    # END GCLOUD USER CONFIG
    & $buzzerGcloud auth login --brief
    if ($LASTEXITCODE -ne 0) { throw 'Google CLI 登入或儲存憑證失敗，請查看上方錯誤並確認設定目錄可寫入。' }

    $buzzerServiceAccount = (Read-Host '輸入已分享試算表且已授權的服務帳戶電子郵件').Trim()
    if ($buzzerServiceAccount -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.iam\.gserviceaccount\.com$') {
        throw '服務帳戶電子郵件格式不正確，請從 Google Cloud 複製完整地址。'
    }
    Remove-Item Env:BUZZER_GOOGLE_ACCESS_TOKEN -ErrorAction SilentlyContinue
    try {
        $env:BUZZER_IAM_SOURCE_TOKEN = & $buzzerGcloud auth print-access-token
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($env:BUZZER_IAM_SOURCE_TOKEN)) {
            throw '目前 Google 帳號無法取得權杖，請重新登入。'
        }
        $buzzerBody = @{
            scope = @(
                'https://www.googleapis.com/auth/spreadsheets'
                'https://www.googleapis.com/auth/drive.metadata.readonly'
            )
            lifetime = '3600s'
        } | ConvertTo-Json
        $env:BUZZER_GOOGLE_ACCESS_TOKEN = (Invoke-RestMethod -Method Post -ErrorAction Stop `
            -Uri "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${buzzerServiceAccount}:generateAccessToken" `
            -Headers @{ Authorization = "Bearer $env:BUZZER_IAM_SOURCE_TOKEN" } `
            -ContentType 'application/json' -Body $buzzerBody).accessToken
        if ([string]::IsNullOrWhiteSpace($env:BUZZER_GOOGLE_ACCESS_TOKEN)) {
            throw 'Google 未回傳權杖。'
        }
    } catch {
        Remove-Item Env:BUZZER_GOOGLE_ACCESS_TOKEN -ErrorAction SilentlyContinue
        throw '申請權杖失敗。請核對登入帳號的 Token Creator 權限、服務帳戶地址及 IAM Service Account Credentials API。'
    } finally {
        Remove-Item Env:BUZZER_IAM_SOURCE_TOKEN -ErrorAction SilentlyContinue
    }

    if ([string]::IsNullOrWhiteSpace($env:BUZZER_TEACHER_PASSWORD)) {
        $buzzerPassword = Read-Host '設定這次展示的老師管理密碼' -AsSecureString
        $env:BUZZER_TEACHER_PASSWORD = [System.Net.NetworkCredential]::new('', $buzzerPassword).Password
        Remove-Variable buzzerPassword
    }
    if ([string]::IsNullOrWhiteSpace($env:BUZZER_TEACHER_PASSWORD)) { throw '老師密碼不可空白。' }
    if ([string]::IsNullOrWhiteSpace($env:BUZZER_SECRET_KEY)) {
        $env:BUZZER_SECRET_KEY = & $buzzerPython -c "import secrets; print(secrets.token_urlsafe(48))"
        if ($LASTEXITCODE -ne 0) { throw '無法產生簽章金鑰。' }
    }
    Write-Host '取得服務帳戶短效權杖成功，約 1 小時有效。'
    Write-Host '老師 http://127.0.0.1:5000/teacher  學生 http://127.0.0.1:5000/'
    & $buzzerPython -m flask --app buzzer run --host 127.0.0.1
    if ($LASTEXITCODE -ne 0) { throw '啟動失敗，請查看 Flask 訊息並確認 5000 連接埠可用。' }
}
```
<!-- /unified-startup -->

第一次輸入 Python 路徑時，可在開始功能表搜尋 Python 3.13，開啟檔案位置查看安裝目錄。常見位置為 `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`，以實際安裝為準。從舊電腦複製的 .venv 可能無法使用，請先將該資料夾改名保存，再重新執行上述區塊。

如果看見 `Running on http://127.0.0.1:5000`，代表服務已啟動。PowerShell 持續佔用是正常情況。保持此視窗開啟，去瀏覽器操作老師及學生頁面。

## 7. 權杖、密碼與重新啟動

| 環境變數 | 用途 |
| --- | --- |
| BUZZER_TEACHER_PASSWORD | 老師登入密碼 |
| BUZZER_SECRET_KEY | Cookie 與預覽簽章，沿用同值可延續登入 |
| BUZZER_GOOGLE_ACCESS_TOKEN | 上述流程取得的服務帳戶短效權杖，優先使用 |
| BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON | 選用替代方式，環境變數值為完整 JSON 內容 |

上述區塊將權杖直接指派到環境變數，畫面只顯示取得成功，請勿自行印出環境變數內容。密碼以隱藏方式輸入。程式沒有自動載入 .env。這些設定供同一 PowerShell 與其子程序使用，新筆電或新視窗需重新取得／設定。gcloud 自身登入憑證由 Google Cloud CLI 管理，本流程將 CLI 快取存在 `%LOCALAPPDATA%\GuidedNotesBuzzer\gcloud`，請勿將此目錄加入 Git 或驗收附件。CLOUDSDK_CONFIG 需在同一 PowerShell 生效，上述整段會設定它。[Google 設定目錄說明](https://docs.cloud.google.com/sdk/docs/configurations)

需要續期時先 Ctrl+C 停止 Flask，再在同一專案目錄重新執行第 6 節整段，會取得新的 1 小時權杖，並沿用目前環境中的老師密碼與簽章金鑰。權杖仍有效且只需重啟時，在同一視窗執行下列命令即可。

```powershell
.\.venv\Scripts\python.exe -m flask --app buzzer run --host 127.0.0.1
```

更換 BUZZER_SECRET_KEY 會使舊 Cookie 與未確認預覽失效，可重新登入及加入。SQLite 中的活動與答案仍存在。更新程式後按 Ctrl+F5 重新載入頁面。

## 8. 在同一筆電展示兩組學生

| 使用者 | 瀏覽器工作階段 | 網址 |
| --- | --- | --- |
| 老師 | Chrome 一般視窗 | http://127.0.0.1:5000/teacher |
| 第 1 組 | Chrome 無痕視窗 | http://127.0.0.1:5000/ |
| 第 2 組 | Edge InPrivate 視窗 | http://127.0.0.1:5000/ |

一般分頁共用工作階段，多個 Chrome 無痕視窗也可能共用同一無痕工作階段。不同瀏覽器的隔離工作階段可避免兩組互相切換身分。展示先使用筆電上的三個視窗。127.0.0.1 代表當前電腦，其他同學的手機無法用這個網址連上筆電。

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

### 助教建議驗收順序與預期結果

| 操作 | 預期結果 |
| --- | --- |
| 匯入預覽後取消 | 活動尚未建立，Google 原表未寫入 |
| 確認匯入並建立兩組 | 出現活動識別碼、正確題目與答案格位置 |
| 不同組各交 Q1 | 老師可見兩組答案與台灣時間，學生只見本組答案 |
| 同組再開一個工作階段 | 可同步取得本組最後有效答案與已作答狀態 |
| 第 1 組先交、第 2 組後交、第 1 組修改 | 結束時第 2 組排名在前，第 1 組修改後順位後移 |
| 原答案不變再送出 | 顯示答案未變更，提交時間與順位不更新 |
| 重新選組並用舊分頁草稿送出 | 舊版本送出拒絕，原組既有答案保留 |
| 結束後嘗試送出、重開或換表 | 不允許，下一份表需建立新活動 |
| 預覽回填後取消，再預覽確認 | 取消不寫入，確認才將第一名答案寫入對應答案格 |
| 人工修改預期答案格後回填 | 整批停止並指出衝突，其他格也不寫入 |
| 刪除活動先取消，再確認 | 取消保留資料，確認清除本機活動；原 Google 內容保留 |
| 開放中或回填待核對時刪除 | 操作拒絕並顯示原因 |
| 重新整理活動專屬網址 | 恢復相同活動資料，不重複建立活動 |

跨班展示請每班建立新活動。可從空白範本各建副本，將副本共用給服務帳戶。已回填活動若被手動清空原表，再次回填會因原值不同停止，請以新活動讀取空白表。所有人工驗收請記錄實際結果與去敏截圖。

## 10. 自動測試

```powershell
# 在含有 requirements-dev.txt 的專案根目錄執行
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m pytest -q tests/browser_smoke.py
```

瀏覽器測試需另以 `.\.venv\Scripts\python.exe -m pip install playwright` 安裝 Playwright，並在本機安裝 Google Chrome。browser_smoke 檔名不在預設 pytest 掃描規則，需另外執行第二條。測試用隔離 SQLite 及 Google 替身，不讀寫真實學習單。涵蓋多組並行、同組同步、截止、版本、預覽取消／確認、原格衝突、未知結果、重啟、手機與桌面流程；結果記於驗證文件。

## 11. 人工驗收

依 [人工驗收清單](specs/001-guided-notes-buzzer/checklists/requirements.md) 使用兩份不同位置的 Google Sheets 副本實測。記錄驗證人、日期、活動識別碼、預期／實際結果與去敏截圖。確認真實權限、API 授權、題號與小題標示保留、答案只寫正確格位。自動驗證不等於已由真人驗收。

## 12. 助教與展示常見問題

| 現象 | 處理方式 |
| --- | --- |
| py -3.13 找不到 Python，或 python 指向 3.14 | 第 6 節首次建立環境時輸入實際 Python 3.13 完整路徑 |
| 找不到 gcloud.cmd | 重開 PowerShell，或在第 6 節輸入安裝目錄下 bin/gcloud.cmd 的完整路徑 |
| gcloud.ps1 被執行原則阻擋 | 統一使用 gcloud.cmd |
| 登入成功但 Error saving Application Default Credentials／Permission denied | 更新專案後重跑第 6 節，會改用目前使用者的可寫入 CLI 設定目錄。若仍失敗，確認此目錄權限與安全軟體限制 |
| 申請權杖 403 | 確認瀏覽器登入帳號已獲該服務帳戶 Token Creator，且相關 API 已啟用 |
| 申請權杖 400 | 確認服務帳戶地址與 lifetime=3600s，未核准延長時不要要求 43200s |
| 服務帳戶沒有原試算表編輯權 | 新副本明確共用給目前輸入的服務帳戶，授予編輯者，重新貼副本網址 |
| 權杖過期 | Ctrl+C，重跑第 6 節整段，再重新操作匯入／回填 |
| 頁面空白或無法連線 | 確認終端出現 Running on，並使用終端列出的同一個連接埠 |
| 5000 已被使用 | 停止上一個 Flask 程序再啟動 |
| 曾回填後手動清空，同一活動無法再回填 | 原值與上次回填紀錄不同，保護檢查會停止。使用空白副本建立新活動測試 |



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
