# Web API 契約 v3.0

頁面：學生 `/`；老師 `/teacher`；指定活動 `/teacher/activities/<id>`。登入後直接恢復指定活動；不存在回 404，不建立替代活動。

所有寫入需 JSON 物件、同源 Origin（有提供時）及 X-CSRF-Token。錯誤回 `{code,message}`；Google 錯誤也僅回去敏訊息。新寫入成功除建立 201 外為 200。

| 方法與路由 | 輸入／輸出與限制 |
| --- | --- |
| POST /api/teacher/session | password；驗證環境管理密碼 |
| GET /api/activities | 活動 id、name、phase 清單（不含作答或組別資訊） |
| POST /api/guided-notes/inspect | 老師，url → sheets[id,name] |
| POST /api/guided-notes/preview | 老師，url、sheet 可省略於單分頁 → preview、sheet、questions[number,prompt,answer_cell]；不建立活動 |
| POST /api/activities | 老師，name、preview → id,name,phase，201；確認重讀與驗摘要；同 preview 重送回原活動 |
| GET /api/activities/<id>/groups | groups[id,name]、joined；不含加入碼 |
| POST /api/activities/<id>/groups | 老師、ready，name → id,name，201 |
| PUT /api/activities/<id>/groups | 老師、ready，count 1–100，從未有學生加入且無舊申請 → groups；否則 409 |
| DELETE /api/activities/<id>/groups/<team> | 老師、ready，無舊作答／申請；撤銷成員並刪組 |
| POST /api/activities/<id>/join | group 正整數；只更新本人加入，回 group、membership_version；不需 code／核准 |
| POST /api/activities/<id>/open | 老師，ready、至少一題及兩組，且無其他 open |
| POST /api/activities/<id>/answers | number、answer、receipt、group、membership_version、worksheet_version；版本不符 409，open 可新交；同答案新 receipt 回 409 answer_unchanged；成功 receipt 重試回原結果 |
| POST /api/activities/<id>/close | 老師，open → closed；重複 closed 回相同結果 |
| GET /api/activities/<id>/view?audience=teacher | 老師：phase,name,groups,worksheet_version,questions[number,prompt,submissions]；closed 另 ranking、winner、status；can_export、groups_locked |
| GET /api/activities/<id>/view?audience=student | 已加入：group、membership_version；questions 只 mine；closed 額外 own_rank、winner[group,name]、status，不回別組答案／時間／順位 |
| POST /api/activities/<id>/export/preview | 老師、closed → preview、spreadsheet、sheet、warning、changes[number,cell,before,answer]；不對 Google 寫入 |
| POST /api/activities/<id>/export | 老師、closed，preview → written；綁活動、工作階段、版本、摘要與期限，重新預檢再寫 |

membership_version 可省略時按 0 驗證，只適用尚未換組的相容客戶端；換組後缺值拒絕。group／worksheet_version 若提供須符合；現行前端都提供。所有回應 Cache-Control: no-store。判定、同場重新匯入、換組審核及舊輪次查閱路由已移除，呼叫不得執行。錯誤路由通常 404；有其他方法匹配時 405。

DELETE /api/activities/<id>：老師、同源 CSRF、JSON `{confirm:true}`，ready／closed 且無 export_batches 才可刪除。成功 `{deleted:true}`；未確認400、無權403、開放或待核對409、未知活動404。單一交易依外鍵順序清除活動及所有相關本機紀錄，保留識別序號及 Google 內容。
