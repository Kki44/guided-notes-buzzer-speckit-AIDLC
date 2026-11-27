import pytest

from conftest import send
from test_import_join import prepared
from test_ranking_review import answer, setup_round


@pytest.fixture
def export_round(app, teacher, prepared):
    fake, _, _, _ = prepared
    fake.cells = dict(fake.cells)
    calls = []
    def write(spreadsheet, sheet, changes):
        calls.append(changes)
        for row, col, value in changes:
            fake.cells[(row, col)] = {"stringValue": value}
    fake.write = write
    path, a, b, student, other = setup_round(app, teacher, prepared)
    answer(student, path, "=first", "a1")
    answer(other, path, "second", "b1", "Q3")
    send(teacher, path + "/close")
    return fake, path, a, b, calls


def send_export(teacher, path):
    result = send(teacher, path + "/export/preview")
    if result.status_code != 200:
        return result
    return send(teacher, path + "/export", {"preview": result.json["preview"]})


def test_export_requires_preview_and_is_idempotent(teacher, export_round):
    fake, path, a, b, calls = export_round
    assert send(teacher, path + "/export").status_code == 400
    assert not calls
    assert send_export(teacher, path).json["written"] == 2
    assert fake.cells[(0, 3)] == {"stringValue": "=first"}
    assert fake.cells[(5, 7)] == {"stringValue": "second"}
    assert send_export(teacher, path).json["written"] == 0


@pytest.mark.parametrize("point, value", [((0, 3), {"formulaValue": '="{{Q1}}"'}), ((0, 0), {"stringValue": "Q2"})])
def test_export_conflicts_prevent_every_write(teacher, export_round, point, value):
    fake, path, a, b, calls = export_round
    fake.cells[point] = value
    response = send_export(teacher, path)
    assert response.status_code == 409 and "Q1" in response.json["message"]
    assert calls == []


@pytest.mark.parametrize("applied, expected", [("all", 200), ("none", 503), ("some", 409)])
def test_uncertain_export_is_reconciled(app, teacher, export_round, applied, expected):
    from buzzer.sheets import SheetsError

    fake, path, a, b, calls = export_round
    write = fake.write
    def timeout(spreadsheet, sheet, changes):
        if applied != "none":
            write(spreadsheet, sheet, changes if applied == "all" else changes[:1])
        raise SheetsError("回應中斷", uncertain=True)
    fake.write = timeout
    assert send_export(teacher, path).status_code == expected
    fake.write = write
    if applied == "some":
        assert send_export(teacher, path).status_code == 409
        assert len(calls) == 1
    else:
        expected_written = 0 if applied == "all" else 2
        assert send_export(teacher, path).json["written"] == expected_written


def test_google_batch_uses_literal_values(monkeypatch):
    from buzzer.sheets import GoogleSheets

    sheets = GoogleSheets()
    def request(method, url, **kwargs):
        assert method == "POST" and url.endswith("/sample:batchUpdate")
        updates = kwargs["json"]["requests"]
        assert len(updates) == 3
        assert updates[0]["updateCells"] == {
            "start": {"sheetId": 7, "rowIndex": 1, "columnIndex": 4},
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "=1+1"}}]}],
            "fields": "userEnteredValue",
        }
        assert updates[2]["updateCells"]["rows"] == [{"values": [{}]}]
    monkeypatch.setattr(sheets, "request", request)
    sheets.write("sample", 7, [(1, 4, "=1+1"), (2, 3, "text"), (4, 6, None)])
