# Guided Notes 搶答系統章程

## Core Principles

### I. PlantUML 設計優先（Design-First with PlantUML）

在 `speckit.specify` 階段，必須使用 PlantUML 語法建立組件圖、類別圖與時序圖。
所有圖表來源（`.puml`）必須存放於專案根目錄的 `./diagrams/`。
建立或更新圖表後，必須執行以下指令，將目錄內所有 `.puml` 渲染成同目錄的 PNG。

```sh
java -jar plantuml.jar "./diagrams/*.puml"
```

### II. 測試與驗收

每次程式改動必須新增或更新相關測試。每個功能至少涵蓋一個正常案例與一個邊界案例。
交付前必須執行完整測試套件並確認全數通過。交付時必須回報實際測試指令與結果。
核心課堂流程必須經人工驗收，包含使用另一份 Guided Notes 驗證匯入與回填。

### III. 輸入驗證與錯誤訊息

每個功能必須驗證輸入，並在驗證失敗時提供清楚的錯誤訊息。
錯誤訊息必須讓使用者辨識問題，且不得包含機敏值。

### IV. 機敏資料

機敏資料只能透過環境變數提供。程式碼、文件、Git 儲存庫與日誌不得包含機敏值。

### V. 變更可追蹤

每項改動必須建立對應的 Git commit，並在交付時回報 commit SHA。

## Additional Constraints

Guided Notes 採用 Google Sheets。匯入和回填必須依工作表的題號、題目及作答欄或既有標記建立對應，
以支援題目位置不同的試算表。課堂活動可以在本機模擬。

## Development Workflow

專案採用 AIDLC+ 的 Diagram First Development，並依序執行下列 SpecKit 階段。

1. `speckit.specify` 必須完成組件圖、類別圖、時序圖與相應的 PNG。
2. `speckit.plan` 必須以這些圖表為主要藍圖，據以規劃應用程式架構與組件。
3. `speckit.implement` 完成程式碼後，必須逐圖比對組件及其依賴、類別及其關係，以及
   互動的順序與條件。必須修正所有差異、重新驗證，並記錄比對結果，確認最終程式碼與圖表完全一致。

## Governance

規格、規劃與實作審查必須檢查本章程。章程修訂須記錄變更內容及原因，經專案負責人確認後提交。
不相容的規則變更提升主版本，新增或擴充規則提升次版本，文字釐清提升修訂版本。

**Version**: 1.1.0 | **Ratified**: 2026-11-12 | **Last Amended**: 2026-11-12
