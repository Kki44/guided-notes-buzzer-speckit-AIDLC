# SDS 系統設計規格書 v3.0

日期：2026-11-26。依據 [SRS](spec.md) 及 [組件](../../diagrams/component.png)、[類別](../../diagrams/class.png)、[時序](../../diagrams/sequence.png) 圖實作。

## 架構與子功能
沿用單一 Flask 程序，同源 Jinja／原生 JavaScript、SQLite WAL、Google Sheets／Drive。老師 `/teacher` 及活動專屬網址；學生 `/`。快照約每秒輪詢，學生 GET 有 8 秒逾時重試。Google 只供匯入及回填，已建立活動的搶答核心使用本機快照。

| 組件 | 檔案與責任 |
| --- | --- |
| 工廠與設定 | buzzer/__init__.py、config.py：環境變數、SQLite、EventOrder、export_lock、Google、靜態檔版本 |
| 權限／活動協調 | routes.py、access.py：角色、CSRF、活動範圍、預覽確認、組別、直接換組、提交與截止 |
| 預覽 | previews.py：SHA256 內容摘要、itsdangerous 簽章、工作階段綁定、20 分鐘期限；只保存業務識別與摘要，不含 Google 憑證 |
| 提交／結算 | activity.py、submissions.py、review.py：單程序入口序列化，交易內配發持久有效 sequence，最後答案、收據、固定第一名 |
| 原表定位／回填 | guided_notes.py：解析、plan_export、prepare_export 預檢、export_notes 確認摘要、字面值批次寫入與不明結果核對 |
| 外部服務 | sheets.py：原生型別、編輯能力、合併／保護、原始值讀取、Google 錯誤去敏 |
| 持久資料 | store.py：12 表、外鍵、BEGIN IMMEDIATE、WAL、相容遷移；保留退役表及欄位 |
| 介面 | teacher.js、student.js 及 templates：預覽／取消／確認、批次組別、網址恢復、作答卡與分頁同步 |

## 藍圖與實作約束
- 匯入時先 parse、回傳題號／題目／答案格及簽章；確認重新讀取並驗摘要，單一交易建立活動與題目。activities.import_key 使相同確認重試回相同活動；新預覽有獨立 nonce。
- ready → open → closed。至少兩組與一題、全系統唯一 open；重複 close 不重算。下一份表另建活動。
- activities.joined_once 在首次成功加入時永久設為 1；即使刪組撤銷成員亦不解除整批重建鎖。舊資料由現存成員／收據／提交／申請回補。
- 直接換組在同一交易驗證組別及更新本人 memberships.version；原組答案不搬移。舊分頁版本不符拒絕並清除草稿，A→B→A 不可繞過。
- 提交先驗證版本與收據，closed 只回既有成功收據；同答案新收據不改資料。新有效序號在交易內更新 identifiers(kind=submissions)，依序號排名，時鐘只供顯示。
- 截止後第一名成功，老師只看結果。學生 API 僅本組提交、名次及得主組名；不回其他組答案／時間／順位。
- prepare_export 與 export_notes 共用計畫、原格驗證與相鄰格遷移；確認要求相同摘要及活動版本，export_lock 防同程序並行回填。預覽不對 Google 寫入；若有舊不明批次可核對並更新本機紀錄。
- 題號、題目或原值／保護有衝突停止整批；批次先持久化再呼叫 Google，未知回應重讀核對。無法以跨服務交易阻止外部使用者在讀寫之間編輯，因此介面要求暫停共同編輯。

## 舊資料
transfer_requests、round_history、rankings.correct 不刪除；停止新增／判定流程。舊輪次不提供介面或查閱 API，僅供資料相容留存；舊活動仍依原保存順位取第一名。新 closed 活動不可改組設定或更換題目。

## 驗證
對照 [需求追蹤](traceability.md)、[任務計畫](../../docs/superpowers/plans/2026-11-26-core-alignment.md) 及 pytest／Playwright。圖表來源及 PNG 同步；未宣稱已完成真實 Google 人工驗收。

## 活動刪除擴充
老師確認後，由 EventOrder → export_lock → BEGIN IMMEDIATE 驗證非 open 且無待核對回填，依 rankings、exports、submissions、receipts、transfer_requests、round_history、memberships、questions、groups、activities 的外鍵順序清除。UI 取消不送出請求，刪除中阻擋輪詢舊回應，完成回建立新活動。只刪本機資料，Google 不變。
