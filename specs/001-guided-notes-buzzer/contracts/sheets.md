# Google Sheets 契約 v3.0

## 授權與讀取
憑證僅來自環境變數，短效權杖優先；不保存或輸出憑證。Drive 檢查原生 Sheets 型別及 canEdit，Sheets 依穩定 sheet ID 讀取原始 userEnteredValue、合併與保護範圍。多分頁須選單張。API 呼叫有逾時與去敏錯誤。

## 匯入
preview 解析唯一「題號／題目／作答」表頭或既有成對標記，回題號、題目、答案格。native source 保存題號／題目及小題錨點、原值。合併格只寫左上；G 小題標示與 H 答案分欄時寫 H，絕不覆蓋標示。確認重讀解析摘要，不一致拒絕建立活動。

## 回填
closed 每題固定第一名為搶答成功來源，未判定正確性。無提交格不寫。prepare_export 讀舊寫入狀態及原表，先核對 pending batch、遷移舊相鄰格 mapping，再驗證全部錨點、原格與保護；回填預覽顯示目標表、格位、前值與答案，不發 Google write。

確認需有效簽章與相同活動版本；重做 prepare_export，若摘要或原格不同停止。保存 export_batches 的前值、目標值後，單次 batchUpdate 以 stringValue 寫字面值，公式樣式答案不執行。成功才更新 exports、必要 mapping 並清除 pending。明確失敗移除 pending；未知結果重讀核對：全部目標吻合則確認成功，全部前值吻合仍可能有延遲原請求，當次保留 pending 提示核對；混合／外部修改回衝突，不盲目重送。

跨 Google 與本機無分散式交易，老師應暫停共同編輯。自動測試以 FakeSheets 驗證字面值、整批衝突、未知結果、重啟核對，真實 Google 權限及原格需另行人工驗收。
