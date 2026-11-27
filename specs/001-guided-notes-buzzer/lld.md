# LLD 細部設計 v3.0

## 路由與流程
詳見 [Web 契約](contracts/web.md)。routes.py 驗證資料與身分後呼叫共用函式。輸入字串需非空、UTF-8 有效，名稱／題號最多 200 字、答案最多 4,000 字、receipt 最多 100 字；組別 ID 必須正整數且小於 2^63，工作表 ID 為 0 至 2^31−1 整數，布林不視為整數。

## 函式責任
| 函式 | 契約 |
| --- | --- |
| read_import(data) | URL／sheet → spreadsheet、sheet、解析 tuple 清單；檢查分頁存在及格式／編輯權 |
| previews.sign(kind,data)／verify(kind,token) | 綁 csrf 識別摘要、用途 salt、20 分鐘期限；驗證失敗 409，缺少／無效型別 400 |
| previews.digest(value) | 穩定排序 JSON 的 SHA256；只比對業務資料，不產生憑證 |
| create_activity() | 確認預覽；重讀來源摘要比對；import_key 唯一，確認重試回原活動 |
| replace_groups(activity) | 1–100 組；ready 且無 memberships／舊申請時交易重建 |
| join_group(activity) | 有效同活動組別；同組重送不增版，不同組 version++，清除本人舊 receipts，保留所有組答案 |
| submit_answer(activity) | 同步交易驗證身分版本、receipt、phase、question、相同答案；只有新有效提交配發 identifiers 序號 |
| lock_rankings(db,activity) | ROW_NUMBER 分題 ORDER BY sequence，保存 rank；outcome 直接取第一筆 |
| activity_view(activity) | 一致讀取快照；teacher 有完整提交／順位，student 只有 mine／own_rank／winner 組名 |
| prepare_export(store,sheets,activity) | 核對不明批次、規劃 changes、讀原格／錨點／保護、遷移相鄰格；不發 Google 寫入 |
| export_notes(...,expected_digest) | 重做 prepare_export，比較摘要後持久待確認批次並字面值寫入；成功落 exports，未知結果核對 |

## 錯誤與並行
所有寫入需要同源 CSRF。老師動作需要老師 session。會員版本與組別不符回 group_changed；未知活動／組別／題號回明確錯誤；phase 非法回 409。成功 receipt 查核先於 closed 拒絕，但先確認目前組別版本。相同答案回 answer_unchanged 且不保存新收據。提交與關閉共用 EventOrder → SQLite 交易順序；寫回以 export_lock 保護。資料庫序號是順位權威，EventOrder 的入口序號不作為有效提交序號。

## 介面
teacher.js 狀態：importPreview、exportPreview、selected activity、viewRequest。輸入／活動切換取消舊預覽；按確認時使用捕捉的活動與 token，請求中停用按鈕。DOM 以 textContent 顯示答案避免注入。student.js 將單一答案表單置入題卡，切換題號或組別版本時清除不適用草稿；重送沿用 receipt；成功後保留卡片預覽。暫時錯誤由下一次輪詢恢復。
