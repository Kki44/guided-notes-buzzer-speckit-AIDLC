# 資料模型｜目前實作 v3.0

**日期**：2026-11-26。[類別圖](../../diagrams/class.png) 對應 `buzzer/store.py` 的實際 SQLite 表，不代表存在同名 Python／ORM 類別。座標皆為零起算，對使用者顯示時轉成 A1。

## 表、主鍵與用途

| 表 | 主鍵 | 主要欄位與不變條件 |
| --- | --- | --- |
| activities | id | name、phase、spreadsheet、sheet、revision；遷移加入 worksheet_version、import_key（唯一預覽摘要；確認重試不重建）、joined_once（曾有學生加入，永久鎖批次重建）。partial unique index 限一筆 open |
| groups | id | activity 外鍵、name；同活動名稱唯一，不使用組別加入碼 |
| memberships | browser + activity | team 外鍵；遷移加入 version 預設 0。browser 使用工作階段 CSRF 識別，不可公開 |
| transfer_requests | id AUTOINCREMENT | activity、browser、source／target 外鍵、status；保留舊申請唯讀，不再新增或審核 |
| questions | id | activity、number、label_row／col、answer_row／col、marker、source；同活動題號與答案格分別唯一 |
| submissions | question + team | answer、timestamp（epoch 奈秒）、sequence（唯一）；同組同題 UPSERT 僅保存最後有效提交 |
| receipts | activity + browser + receipt | number、answer、response JSON；網路重試回原結果，內容不符拒絕 |
| rankings | question + team | rank；correct NULL／0／1 為停用的舊資料欄位；(question, team) 複合外鍵指 submissions，同題 rank 唯一 |
| exports | question（亦為外鍵） | written、revision；上次成功寫入內容，供原值與故障核對 |
| export_batches | activity（亦為外鍵） | spreadsheet 唯一、sheet、revision、changes JSON；保存前值與目標值供故障後核對 |
| round_history | id | activity 外鍵、snapshot JSON；僅資料相容留存；不提供介面、查閱 API 或新增輪次 |
| identifiers | kind | last_id；配發 activities、groups、submissions 序號；只有有效新提交才增加 submissions 序號 |

沒有 ON DELETE CASCADE；ready 可刪組並撤銷入組，ready／closed 活動在無待確認回填且確認後可依外鍵順序刪除相關資料；有既有作答／申請者拒絕刪除。所有 read 連線啟用 foreign_keys；寫入交易使用 BEGIN IMMEDIATE；WAL 在初始化啟用。

## JSON 結構

| 欄位 | 結構／語意 |
| --- | --- |
| questions.source | null 或 `{anchors: [[[row,col], 原始 userEnteredValue], ...], original: 原答案標示或 null}`。anchors 至少包含題號與題目，拆分小題時亦可能包含原小題標示 |
| receipts.response | `{answer, timestamp, sequence}`，不含老師權限或加入碼 |
| export_batches.changes | 每格的 question、number、label、cell、expected、desired、anchors、restore、subquestion_label，必要時含 new_source／label_only |
| round_history.snapshot | spreadsheet、sheet、questions；每題有 number、source、答案格與 ranking（組別、名稱、答案、時間、順位、判定） |

## 版本與相容遷移
- worksheet_version：保留舊欄位，新活動匯入時為 1，提交可驗證題目版本。
- memberships.version：直接換組時遞增，舊分頁及 A→B→A 版本均拒絕。
- activities.revision：有效提交、組別批次、刪組及階段變更時遞增；回填預覽綁版本。
- import_key：確認 token 的 SHA256，唯一索引使重試不重建活動；舊活動為 null。
- SQLite 初始化只加欄位／索引／序號，保留所有既有資料。舊判定不再影響成功組別，舊輪次快照內容不改寫。
