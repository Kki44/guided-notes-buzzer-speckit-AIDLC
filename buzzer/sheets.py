from dataclasses import dataclass
import json
import os
import re

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials as AccessTokenCredentials
from google.oauth2.service_account import Credentials
from requests.exceptions import RequestException


class SheetsError(Exception):
    def __init__(self, message, status=503, uncertain=False):
        self.message = message
        self.status = status
        self.uncertain = uncertain


@dataclass
class Grid:
    cells: dict
    editable: object
    merges: tuple = ()


def contains(area, row, col):
    return (
        area.get("startRowIndex", 0) <= row < area.get("endRowIndex", float("inf"))
        and area.get("startColumnIndex", 0) <= col < area.get("endColumnIndex", float("inf"))
    )


def editable_cell(protections, row, col):
    for protection in protections:
        if protection.get("warningOnly") or protection.get("requestingUserCanEdit"):
            continue
        if contains(protection.get("range", {}), row, col) and not any(
            contains(area, row, col) for area in protection.get("unprotectedRanges", [])
        ):
            return False
    return True


class GoogleSheets:
    base = "https://sheets.googleapis.com/v4/spreadsheets"
    spreadsheet_mime_type = "application/vnd.google-apps.spreadsheet"

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or self._authorize

    @staticmethod
    def _authorize():
        token = os.environ.get("BUZZER_GOOGLE_ACCESS_TOKEN")
        if token is not None:
            if not re.fullmatch(r"[A-Za-z0-9._~+/\-]+=*", token):
                raise SheetsError("Google 短效權杖格式不正確，請重新取得權杖。")
            return AuthorizedSession(AccessTokenCredentials(token), refresh_status_codes=())
        raw = os.environ.get("BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise SheetsError("請設定 Google 服務帳戶 JSON 或短效權杖 BUZZER_GOOGLE_ACCESS_TOKEN。")
        try:
            info = json.loads(raw)
            required = ("client_email", "token_uri", "private_key")
            if not isinstance(info, dict) or not all(isinstance(info.get(key), str) for key in required):
                raise ValueError("Invalid credentials")
            credential = Credentials.from_service_account_info(info, scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
            ])
        except (ValueError, TypeError, GoogleAuthError, KeyError):
            raise SheetsError("Google 服務帳戶憑證格式不正確。") from None
        return AuthorizedSession(credential)

    def request(self, method, url, **kwargs):
        try:
            with self.session_factory() as client:
                response = client.request(method, url, timeout=15, **kwargs)
        except GoogleAuthError:
            raise SheetsError("Google 服務帳戶驗證失敗，請檢查憑證。") from None
        except RequestException:
            raise SheetsError("Google Sheets 連線失敗，請稍後重試。", uncertain=method == "POST") from None
        if response.status_code == 401:
            raise SheetsError("Google 驗證失敗：短效權杖可能已過期，請重新取得；若使用 JSON，請檢查憑證。", 403)
        if response.status_code in (403, 404):
            raise SheetsError("找不到原試算表或服務帳戶無權操作，請檢查分享權限。", 403)
        if response.status_code == 400:
            if url.startswith("https://www.googleapis.com/drive/"):
                raise SheetsError("Google Drive 拒絕讀取檔案資訊，請確認貼上的是完整的試算表連結。", 400)
            if method == "GET":
                raise SheetsError("Google Sheets 拒絕讀取工作表，請確認使用原生 Google 試算表並重新選擇工作表。", 400)
            raise SheetsError("Google Sheets 拒絕操作，請確認工作表與儲存格設定。", 409)
        if not response.ok:
            raise SheetsError("Google Sheets 暫時無法操作。", uncertain=method == "POST")
        try:
            return response.json()
        except ValueError:
            raise SheetsError("Google Sheets 回應無法辨識。", uncertain=method == "POST") from None

    def inspect(self, spreadsheet):
        drive_url = f"https://www.googleapis.com/drive/v3/files/{spreadsheet}"
        drive = self.request("GET", drive_url, params={
            "fields": "mimeType,capabilities(canEdit)", "supportsAllDrives": "true",
        })
        if drive.get("mimeType") != self.spreadsheet_mime_type:
            raise SheetsError("此連結不是原生 Google 試算表。若畫面顯示 .XLSX，請用「檔案 → 另存為 Google 試算表」，再貼上新副本的連結。", 400)
        if not drive.get("capabilities", {}).get("canEdit"):
            raise SheetsError("服務帳戶沒有原試算表的編輯權。", 403)
        data = self.request("GET", f"{self.base}/{spreadsheet}", params={
            "fields": "sheets(properties(sheetId,title,sheetType))",
        })
        return [
            {"id": props["sheetId"], "name": props["title"]}
            for sheet in data.get("sheets", [])
            if (props := sheet["properties"]).get("sheetType") == "GRID"
        ]

    def read(self, spreadsheet, sheet):
        choices = self.inspect(spreadsheet)
        title = next((choice["name"] for choice in choices if choice["id"] == sheet), None)
        if title is None:
            raise SheetsError("找不到原工作表。", 409)
        quoted = title.replace("'", "''")
        data = self.request("GET", f"{self.base}/{spreadsheet}", params={
            "ranges": f"'{quoted}'",
            "fields": (
                "sheets(properties(sheetId),protectedRanges,merges,"
                "data(startRow,startColumn,rowData(values(userEnteredValue)))"
                ")"
            ),
        })
        grid = next((entry for entry in data.get("sheets", []) if entry["properties"]["sheetId"] == sheet), None)
        if grid is None:
            raise SheetsError("工作表位置已變更，請重新檢查。", 409)
        cells = {}
        for block in grid.get("data", []):
            for row, row_data in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                for col, cell in enumerate(row_data.get("values", []), block.get("startColumn", 0)):
                    if value := cell.get("userEnteredValue"):
                        cells[(row, col)] = value

        def editable(row, col):
            if not editable_cell(grid.get("protectedRanges", []), row, col):
                return False
            return not any(
                contains(area, row, col)
                and (row, col) != (area.get("startRowIndex", 0), area.get("startColumnIndex", 0))
                for area in grid.get("merges", [])
            )
        return Grid(cells, editable, tuple(grid.get("merges", [])))

    def write(self, spreadsheet, sheet, changes):
        updates = [
            {"updateCells": {
                "start": {"sheetId": sheet, "rowIndex": row, "columnIndex": col},
                "rows": [{"values": [
                    {} if value is None else {"userEnteredValue": {"stringValue": value}},
                ]}],
                "fields": "userEnteredValue",
            }}
            for row, col, value in changes
        ]
        self.request("POST", f"{self.base}/{spreadsheet}:batchUpdate", json={"requests": updates})
