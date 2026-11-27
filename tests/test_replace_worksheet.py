from conftest import send
from test_import_join import prepared, create_notes, URL
from test_ranking_review import setup_round, answer


def test_next_sheet_creates_distinct_activity_and_preserves_previous(app, teacher, prepared):
    fake, *_ = prepared
    path, team, _, student, _ = setup_round(app, teacher, prepared)
    answer(student, path, "old answer", "old")
    send(teacher, path + "/close")
    fake.cells = {(3, 0): {"stringValue": "Q8"}, (3, 5): {"stringValue": "{{Q8}}"}}
    new, a, b = create_notes(teacher, "Next")
    assert new != path
    assert teacher.get(new + "/view").json["questions"][0]["number"] == "Q8"
    old = student.get(path + "/view").json
    assert old["phase"] == "closed" and old["questions"][0]["mine"]["answer"] == "old answer"
    assert send(teacher, path + "/guided-notes", {"url": URL}).status_code == 404
    assert send(teacher, path + "/open").status_code == 409
    assert send(teacher, new + "/open").status_code == 200


def test_only_one_activity_can_open_and_invalid_preview_does_not_change_old(app, teacher, prepared):
    fake, path, *_ = prepared
    new, *_ = create_notes(teacher, "Next")
    assert send(teacher, path + "/open").status_code == 200
    assert send(teacher, new + "/open").json["code"] == "another_open"
    fake.cells = {}
    assert send(teacher, "/api/guided-notes/preview", {"url": URL}).status_code == 400
    assert len(teacher.get(path + "/view").json["questions"]) == 2
    assert teacher.get(path + "/history").status_code == 404
