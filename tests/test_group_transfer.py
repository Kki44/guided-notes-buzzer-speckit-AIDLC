"""Direct re-selection replaces approval; persisted legacy records remain untouched."""
import pytest
from conftest import send
from test_import_join import prepared, create_notes
from test_ranking_review import join, answer, setup_round


def test_switch_changes_only_requester_and_preserves_group_answers(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    teammate = join(app, path, a)
    answer(student, path, "A answer", "a")
    assert send(student, path + "/join", {"group": b["id"]}).json["membership_version"] == 1
    assert teammate.get(path + "/view").json["questions"][0]["mine"]["answer"] == "A answer"
    assert student.get(path + "/view").json["questions"][0]["mine"] is None
    assert send(student, path + "/answers", {"number": "Q1", "answer": "stale", "receipt": "stale"}).json["code"] == "group_changed"
    view = student.get(path + "/view").json
    assert send(student, path + "/answers", {"number": "Q1", "answer": "B answer", "receipt": "fresh", "group": b["id"], "membership_version": view["membership_version"]}).status_code == 200
    assert other.get(path + "/view").json["questions"][0]["mine"]["answer"] == "B answer"


@pytest.mark.parametrize("value", [None, True, 0, "2", 2**63])
def test_join_validates_group(app, teacher, prepared, value):
    _, path, a, _ = prepared
    student = join(app, path, a)
    assert send(student, path + "/join", {"group": value}).status_code == 400
    assert student.get(path + "/groups").json["joined"] == a["id"]


def test_foreign_group_rejected_and_same_group_is_idempotent(app, teacher, prepared):
    _, path, a, _ = prepared
    student = join(app, path, a)
    _, foreign, _ = create_notes(teacher, "Other")
    assert send(student, path + "/join", {"group": foreign["id"]}).status_code == 404
    assert send(student, path + "/join", {"group": a["id"]}).json["membership_version"] == 0
    assert send(student, path + "/transfer-requests", {"group": foreign["id"]}).status_code == 404


def test_reselection_version_persists_after_server_restart(app, teacher, prepared):
    from buzzer import create_app
    _, path, a, b = prepared
    student = join(app, path, a)
    send(student, path + "/join", {"group": b["id"]})
    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    client = restarted.test_client()
    with student.session_transaction() as old, client.session_transaction() as new:
        new.update(old)
    view = client.get(path + "/view?audience=student").json
    assert view["group"]["id"] == b["id"] and view["membership_version"] == 1
