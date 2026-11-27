import pytest

from conftest import send


URL = "https://docs.google.com/spreadsheets/d/test-sheet/edit"


class FakeSheets:
    cells = {(0, 0): {"stringValue": "Q1"}, (0, 3): {"stringValue": "{{Q1}}"},
             (4, 1): {"stringValue": "Q3"}, (5, 7): {"stringValue": "{{Q3}}"}}
    can_edit = True
    protected = set()

    def inspect(self, spreadsheet):
        assert spreadsheet == "test-sheet"
        return [{"id": 0, "name": "Notes"}] if self.can_edit else []

    def read(self, spreadsheet, sheet):
        from buzzer.sheets import Grid
        return Grid(dict(self.cells), lambda row, col: (row, col) not in self.protected)


def create_notes(teacher, name="Class"):
    result = send(teacher, "/api/guided-notes/preview", {"url": URL, "sheet": 0})
    assert result.status_code == 200, result.json
    response = send(teacher, "/api/activities", {"name": name, "preview": result.json["preview"]})
    assert response.status_code == 201, response.json
    path = f"/api/activities/{response.json['id']}"
    a = send(teacher, path + "/groups", {"name": "A"}).json
    b = send(teacher, path + "/groups", {"name": "B"}).json
    return path, a, b


@pytest.fixture
def prepared(app, teacher):
    fake = FakeSheets()
    fake.cells = dict(fake.cells)
    app.extensions["sheets"] = fake
    return fake, *create_notes(teacher)


def test_import_discovery_and_nonconsecutive_questions(teacher, prepared):
    _, path, _, _ = prepared
    assert send(teacher, "/api/guided-notes/inspect", {"url": URL}).json["sheets"][0]["id"] == 0
    assert [q["number"] for q in teacher.get(path + "/view").json["questions"]] == ["Q1", "Q3"]
    assert send(teacher, path + "/open").status_code == 200
    assert send(teacher, path + "/guided-notes", {"url": URL}).status_code == 404


@pytest.mark.parametrize("changes", [
    {(1, 0): {"stringValue": "Q1"}},
    {(1, 0): {"stringValue": "{{Q9}}"}},
    {(0, 3): {"stringValue": "missing"}},
    {(1, 0): {"stringValue": "{{Q1}}"}},
])
def test_import_conflicts_preserve_previous_questions(app, teacher, prepared, changes):
    fake, path, _, _ = prepared
    fake.cells |= changes
    assert send(teacher, "/api/guided-notes/preview", {"url": URL}).status_code == 400
    assert len(teacher.get(path + "/view").json["questions"]) == 2
    assert len(teacher.get("/api/activities").json["activities"]) == 1


def test_import_rejects_wrong_url_and_protected_cells(teacher, prepared):
    fake, *_ = prepared
    assert send(teacher, "/api/guided-notes/inspect", {"url": "https://example.org"}).status_code == 400
    assert send(teacher, "/api/guided-notes/preview", {"url": URL, "sheet": 2}).status_code == 400
    fake.protected = {(0, 3)}
    response = send(teacher, "/api/guided-notes/preview", {"url": URL})
    assert response.status_code == 403 and "D1" in response.json["message"]
    fake.can_edit = False
    assert send(teacher, "/api/guided-notes/preview", {"url": URL}).status_code == 400


def test_join_uses_activity_and_group_without_codes(app, teacher, prepared):
    _, path, a, b = prepared
    student = app.test_client()
    assert student.get(path + "/groups").json["groups"][0] == a
    assert send(student, path + "/join", {"group": a["id"]}).status_code == 200
    assert send(student, path + "/join", {"group": b["id"]}).json["membership_version"] == 1
    assert student.get(path + "/groups").json["joined"] == b["id"]
