import secrets

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    from buzzer import create_app

    monkeypatch.setenv("BUZZER_TEACHER_PASSWORD", secrets.token_urlsafe())
    monkeypatch.setenv("BUZZER_SECRET_KEY", secrets.token_urlsafe())
    return create_app({"TESTING": True, "DATABASE": tmp_path / "test.sqlite3"})


def send(client, path, data=None, method="POST"):
    with client.session_transaction() as session:
        token = session.setdefault("csrf", secrets.token_urlsafe())
    return client.open(path, method=method, json=data or {}, headers={"X-CSRF-Token": token})


@pytest.fixture
def teacher(app):
    import os

    client = app.test_client()
    response = send(client, "/api/teacher/session", {"password": os.environ["BUZZER_TEACHER_PASSWORD"]})
    assert response.status_code == 200
    return client
