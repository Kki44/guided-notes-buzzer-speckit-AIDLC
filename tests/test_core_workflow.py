from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from conftest import send
from test_import_join import create_notes, prepared
from test_ranking_review import answer, setup_round, join
from test_export import send_export


@pytest.mark.parametrize("layout", [
    {(0, 0): "Q1", (0, 3): "{{Q1}}", (5, 0): "Q3", (5, 7): "{{Q3}}"},
    {(10, 4): "Q1", (10, 6): "{{Q1}}"},
])
def test_core_workflow_preserves_unrelated_cells(app, teacher, prepared, layout):
    fake, _, _, _ = prepared
    fake.cells = {point: {"stringValue": text} for point, text in layout.items()}
    fake.cells[(2, 2)] = {"formulaValue": "=2+2"}
    def write(_, __, changes):
        for row, col, value in changes:
            fake.cells[(row, col)] = {"stringValue": value}
    fake.write = write
    path, a, b = create_notes(teacher)
    send(teacher, path + "/open")
    student, other = join(app, path, a), join(app, path, b)
    assert answer(student, path, "wrong", "a").status_code == 200
    assert answer(other, path, "right", "b").status_code == 200
    assert send(teacher, path + "/close").status_code == 200
    assert student.get(path + "/view").json["questions"][0]["winner"]["name"] == "A"
    assert send_export(teacher, path).json == {"written": 1}
    assert fake.cells == {
        **{point: {"stringValue": "wrong" if text == "{{Q1}}" else text} for point, text in layout.items()},
        (2, 2): {"formulaValue": "=2+2"},
    }


def test_queued_submission_is_included_before_close(app, teacher, prepared, monkeypatch):
    path, a, _, student, _ = setup_round(app, teacher, prepared)
    from buzzer import routes

    entered = Event()
    proceed = Event()
    save = routes.save_submission
    def pause(*args, **kwargs):
        entered.set()
        assert proceed.wait(5)
        return save(*args, **kwargs)
    monkeypatch.setattr(routes, "save_submission", pause)
    with ThreadPoolExecutor(2) as executor:
        submitted = executor.submit(answer, student, path, "before", "first")
        assert entered.wait(5)
        closed = executor.submit(send, teacher, path + "/close")
        proceed.set()
        assert submitted.result().status_code == 200
        assert closed.result().status_code == 200
    assert answer(student, path, "after", "second").status_code == 409
    assert student.get(path + "/view").json["questions"][0]["own_rank"] == 1


def test_pending_batch_survives_restart(app, teacher, prepared):
    from buzzer import create_app
    from buzzer.sheets import SheetsError

    fake, _, _, _ = prepared
    path, a, _, student, _ = setup_round(app, teacher, prepared)
    answer(student, path, "accepted", "a")
    send(teacher, path + "/close")
    original_read = fake.read
    def write_then_lose_response(_, __, changes):
        fake.cells = {**fake.cells, **{(row, col): {"stringValue": value} for row, col, value in changes}}
        def unavailable(*args):
            raise SheetsError("offline")
        fake.read = unavailable
        raise SheetsError("offline", uncertain=True)
    fake.write = write_then_lose_response
    assert send_export(teacher, path).status_code == 503
    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    restarted.extensions["sheets"] = fake
    fake.read = original_read
    new_client = restarted.test_client()
    with teacher.session_transaction() as old_session, new_client.session_transaction() as new_session:
        new_session.update(old_session)
    assert send_export(new_client, path).json == {"written": 0}
    assert fake.cells[(0, 3)] == {"stringValue": "accepted"}
    with restarted.extensions["store"].read() as db:
        assert db.execute("SELECT COUNT(*) FROM export_batches").fetchone()[0] == 0
        assert db.execute("SELECT written FROM exports").fetchone()[0] == "accepted"
