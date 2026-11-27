# 需求與測試追蹤 v3.0

| 需求 | 程式 | 正常／邊界證據 |
| --- | --- | --- |
| FR-01 身分與機密 | config、access、routes | test_foundation、test_sheets_read：登入、CSRF、錯誤憑證及去敏 |
| FR-02 匯入預覽確認 | routes、previews、guided_notes | test_import_join、test_core_alignment、test_native_notes：預覽不建活動、無效／來源變更／跨工作階段拒絕、合併與分欄 |
| FR-03 單向生命週期 | routes | test_foundation、test_ranking_review、test_replace_worksheet：兩組開放、重複 close、拒絕重開與第二場 open |
| FR-04 組別設定 | routes | test_core_alignment、test_activity_management：批次與逐組、0／101／布林、已有成員鎖重建、僅準備刪組 |
| FR-05 加入與改組 | routes、student.js | test_group_transfer、test_core_alignment、browser_smoke：直換只移動本人、外活動拒絕、舊版本與 A→B→A、防分頁誤送 |
| FR-06 最後答案與重試 | routes、submissions | test_ranking_review、test_core_alignment：修改、空白、重送、相同答案並行只接受一次 |
| FR-07 序號與截止 | activity、store、review | test_core_workflow、test_core_alignment：並行截止、序號、時鐘倒退、時間顯示 |
| FR-08 固定第一名 | review、routes | test_ranking_review、test_activity_management：第一名直接成功、判定 API 移除、舊判定保留不影響結果 |
| FR-09 資料隔離 | routes | test_classroom_sync、test_core_alignment：八組同步、同瀏覽器老師登入仍只看學生權限、得主僅組名 |
| FR-10 卡片同步 | student.js、classroom.css | browser_smoke：作答痕跡、同組同步、改組清草稿、手機不溢出 |
| FR-11 預覽回填 | guided_notes、previews、teacher.js | test_export、test_native_notes、test_core_workflow、browser_smoke：取消無寫入、字面值、原格衝突、不明結果與重啟核對 |
| FR-12 恢復與持久 | store、routes、teacher.js | test_core_alignment、test_replace_worksheet、browser_smoke：指定網址重整、未知活動、不同表活動獨立 |
| FR-13 舊資料保留 | store、routes | test_activity_management、test_teacher_progress：申請／判定／輪次保留，退役操作不提供 |

執行指令及實際結果見 [validation](validation.md)。人工 Google 驗收與自動測試分開記錄；不把尚未真人執行的操作列為通過。

FR-14 活動刪除 → routes.delete_activity、teacher.js：test_activity_management 正常刪除／其他活動與 Google 不受影響、角色／CSRF／確認／open／pending 邊界；browser_smoke 驗證取消與確認及回到新活動。
