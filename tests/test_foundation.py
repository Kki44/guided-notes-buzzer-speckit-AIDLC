from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import send


def test_configuration_rejects_missing_password(monkeypatch):
    from buzzer.config import settings

    monkeypatch.delenv("BUZZER_TEACHER_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="BUZZER_TEACHER_PASSWORD"):
        settings()


def test_transaction_is_durable_and_rolls_back(app):
    from buzzer.store import Store

    store = app.extensions["store"]
    with store.transaction() as db:
        db.execute("INSERT INTO activities (name) VALUES ('Class')")
    with pytest.raises(ValueError), store.transaction() as db:
        db.execute("INSERT INTO activities (name) VALUES ('Rollback')")
        raise ValueError
    with Store(store.path).read() as db:
        assert [row["name"] for row in db.execute("SELECT name FROM activities")] == ["Class"]


def test_events_are_ordered_and_failure_does_not_block():
    from buzzer.activity import EventOrder

    order = EventOrder(clock=lambda: 100, initial=8)
    with pytest.raises(ValueError), order.receive():
        raise ValueError
    def receive(_):
        with order.receive() as receipt:
            return receipt
    with ThreadPoolExecutor(4) as executor:
        assert sorted(executor.map(receive, range(4))) == [(100, n) for n in range(10, 14)]


def test_teacher_login_requires_csrf_and_correct_password(app, teacher):
    client = app.test_client()
    assert client.post("/api/teacher/session", json={}).status_code == 403
    assert send(client, "/api/teacher/session", {"password": "wrong"}).status_code == 401
    assert teacher.get("/api/activities").status_code == 200


def test_student_page_has_no_teacher_link_and_teacher_page_requires_login(app):
    student = app.test_client()
    page = student.get("/")
    assert page.status_code == 200
    assert 'href="/teacher"' not in page.get_data(as_text=True)
    teacher_page = student.get("/teacher").get_data(as_text=True)
    assert 'id="login"' in teacher_page
    assert 'id="activity"' not in teacher_page


def test_teacher_page_has_no_student_link(teacher):
    page = teacher.get("/teacher").get_data(as_text=True)
    assert 'id="notes"' in page
    assert 'href="/"' not in page


def test_student_script_url_changes_when_frontend_is_updated(app, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    script = static / "student.js"
    script.write_text("first", encoding="utf-8")
    app.static_folder = str(static)
    first = app.test_client().get("/").get_data(as_text=True)
    assert "/static/student.js?v=" in first
    script.write_text("second version", encoding="utf-8")
    second = app.test_client().get("/").get_data(as_text=True)
    assert first != second


def test_invalid_unicode_is_rejected_without_internal_error(app, teacher):
    response = send(teacher, "/api/activities", {"name": chr(0xD800)})
    assert response.status_code == 400
    assert response.json["code"] == "invalid_input"


def test_requires_confirmed_import_and_two_groups(app, teacher):
    from test_import_join import FakeSheets, URL
    app.extensions["sheets"] = FakeSheets()
    assert send(teacher, "/api/activities", {"name": "Class"}).status_code == 400
    token = send(teacher, "/api/guided-notes/preview", {"url": URL}).json["preview"]
    activity = send(teacher, "/api/activities", {"name": "Class", "preview": token}).json["id"]
    path = f"/api/activities/{activity}"
    assert send(app.test_client(), path + "/groups", {"name": "A"}).status_code == 403
    group = send(teacher, path + "/groups", {"name": "A"})
    assert group.status_code == 201 and "code" not in group.json
    assert send(teacher, path + "/groups", {"name": "A"}).status_code == 409
    assert send(teacher, path + "/open").status_code == 409
