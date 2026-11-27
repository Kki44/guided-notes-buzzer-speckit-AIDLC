# 活動刪除實作計畫

使用者明確要求恢復刪除活動功能。沿用 Flask／SQLite 與現有介面。

- [x] Specify：更新 SRS FR-14、活動狀態及類別圖並重新產生 PNG。
- [x] 先寫正常刪除與權限、CSRF、確認、開放中及待回填邊界測試，確認舊實作失敗。
- [x] 以 EventOrder／export_lock／資料庫交易依外鍵順序刪除本機相關紀錄，保留 Google、其他活動及遞增 ID。
- [x] 老師按鈕、取消／確認提示；刪除中忽略舊輪詢，成功回新活動。
- [x] 完整 pytest、Chrome 流程及文件驗證通過後建立對應 commit。

驗證：95 項 pytest、2 項 Chrome 流程、5 項文件檢查通過。
