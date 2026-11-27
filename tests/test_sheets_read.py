import secrets
from types import SimpleNamespace

import pytest

from buzzer.sheets import GoogleSheets, SheetsError


def test_google_reader_maps_named_tab_and_typed_cells(monkeypatch):
    sheets = GoogleSheets()
    calls = []

    def request(method, url, **kwargs):
        calls.append(kwargs["params"])
        if "/drive/" in url:
            return {"mimeType": "application/vnd.google-apps.spreadsheet", "capabilities": {"canEdit": True}}
        if "ranges" not in kwargs["params"]:
            return {"sheets": [{"properties": {"sheetId": 2, "sheetType": "GRID", "title": "O'Brien"}}]}
        return {"sheets": [{"properties": {"sheetId": 2},
            "protectedRanges": [{"range": {"startRowIndex": 4, "endRowIndex": 6}}],
            "data": [{"startRow": 4, "startColumn": 3, "rowData": [{"values": [
                {"userEnteredValue": {"formulaValue": "=1"}},
            ]}]}]}]}

    monkeypatch.setattr(sheets, "request", request)
    grid = sheets.read("sheet", 2)
    assert calls[0]["fields"] == "mimeType,capabilities(canEdit)"
    assert calls[-1]["ranges"] == "'O''Brien'"
    assert grid.cells[(4, 3)] == {"formulaValue": "=1"}
    assert not grid.editable(4, 3)
    assert grid.editable(6, 3)


def test_google_reader_requires_edit_permission(monkeypatch):
    sheets = GoogleSheets()
    monkeypatch.setattr(sheets, "request", lambda *args, **kwargs: {
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "capabilities": {"canEdit": False},
    })
    with pytest.raises(SheetsError) as failure:
        sheets.inspect("sheet")
    assert failure.value.status == 403


def test_excel_is_identified_before_calling_sheets_api(monkeypatch):
    sheets = GoogleSheets()

    def request(method, url, **kwargs):
        assert "/drive/" in url
        return {
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "capabilities": {"canEdit": True},
        }

    monkeypatch.setattr(sheets, "request", request)
    with pytest.raises(SheetsError, match="另存為 Google 試算表") as failure:
        sheets.inspect("sheet")
    assert failure.value.status == 400


def test_google_credentials_require_a_json_object(monkeypatch):
    monkeypatch.setenv("BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON", "[]")
    with pytest.raises(SheetsError, match="憑證格式不正確"):
        GoogleSheets().inspect("sheet")


def test_keyless_credentials_apply_the_environment_token(monkeypatch):
    token = secrets.token_urlsafe()
    monkeypatch.delenv("BUZZER_GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("BUZZER_GOOGLE_ACCESS_TOKEN", token)
    with GoogleSheets._authorize() as session:
        headers = {}
        session.credentials.apply(headers)
    assert headers["authorization"] == f"Bearer {token}"


def test_keyless_credentials_reject_invalid_token_without_exposing_it(monkeypatch):
    monkeypatch.setenv("BUZZER_GOOGLE_ACCESS_TOKEN", "invalid\nvalue")
    with pytest.raises(SheetsError, match="權杖格式不正確"):
        GoogleSheets._authorize()


def test_google_unauthorized_explains_that_a_token_may_have_expired():
    class UnauthorizedSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, *args, **kwargs):
            return SimpleNamespace(status_code=401, ok=False)

    with pytest.raises(SheetsError, match="權杖.*過期"):
        GoogleSheets(UnauthorizedSession).inspect("sheet")
