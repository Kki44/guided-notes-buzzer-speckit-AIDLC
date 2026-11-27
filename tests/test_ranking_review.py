from conftest import send
from test_import_join import prepared, create_notes


def join(app, path, group):
    client = app.test_client()
    assert send(client, path + "/join", {"group": group["id"]}).status_code == 200
    return client


def answer(client, path, text, receipt, question="Q1"):
    return send(client, path + "/answers", {"number": question, "answer": text, "receipt": receipt})


def setup_round(app, teacher, prepared):
    _, path, a, b = prepared
    assert send(teacher, path + "/open").status_code == 200
    return path, a, b, join(app, path, a), join(app, path, b)


def test_submissions_are_private_and_idempotent(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    teammate = join(app, path, a)
    assert answer(student, path, " ", "empty").status_code == 400
    assert answer(student, path, "wrong question", "unknown", "Q2").status_code == 404
    first = answer(student, path, " A private ", "first").json
    assert first["answer"] == "A private"
    assert answer(student, path, " A private ", "first").json == first
    assert answer(student, path, "changed", "first").status_code == 409
    assert "A private" not in other.get(path + "/view").get_data(as_text=True)
    assert answer(teammate, path, "A private", "unchanged").status_code == 409
    replacement = answer(teammate, path, "A revised", "second").json
    assert replacement["sequence"] > first["sequence"]
    assert student.get(path + "/view").json["questions"][0]["mine"]["sequence"] == replacement["sequence"]
    assert teacher.get(path + "/view").json["questions"][0]["submissions"][0]["group"] == a["id"]
    assert app.test_client().get(path + "/view").status_code == 403


def test_student_view_is_correct_in_browser_already_logged_in_as_teacher(app, teacher, prepared):
    path, a, _, student, other = setup_round(app, teacher, prepared)
    assert send(teacher, path + "/join", {"group": a["id"]}).status_code == 200
    answer(student, path, "our answer", "a")
    answer(other, path, "other private answer", "b")
    response = teacher.get(path + "/view?audience=student")
    question = response.json["questions"][0]
    assert question["mine"]["answer"] == "our answer"
    assert "other private answer" not in response.get_data(as_text=True)
    assert teacher.get(path + "/view?audience=teacher").json["questions"][0]["submissions"]
    assert student.get(path + "/view?audience=teacher").status_code == 403
    assert student.get(path + "/view?audience=invalid").status_code == 400


def test_close_locks_order_and_retries(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    app.extensions["event_order"].clock = lambda: 100
    first = answer(student, path, "old", "a1").json
    second = answer(other, path, "B", "b1").json
    latest = answer(student, path, "new", "a2").json
    assert first["timestamp"] == second["timestamp"] == latest["timestamp"]
    assert send(teacher, path + "/close").status_code == 200
    view = student.get(path + "/view").json
    assert view["phase"] == "closed"
    assert view["questions"][0]["own_rank"] == 2
    assert "ranking" not in view["questions"][0]
    assert view["questions"][1]["status"] == "empty"
    assert answer(student, path, "new", "a2").json == latest
    assert answer(student, path, "closed", "a3").status_code == 409


def test_teacher_sees_last_received_time_before_and_after_close(app, teacher, prepared):
    path, _, _, student, _ = setup_round(app, teacher, prepared)
    app.extensions["event_order"].clock = lambda: 1_794_969_123_456_789_000
    first = answer(student, path, "first", "first").json
    view = teacher.get(path + "/view").json
    assert view["questions"][0]["submissions"][0]["received_at"] == "2026-11-18T10:32:03.456+08:00"
    app.extensions["event_order"].clock = lambda: first["timestamp"] + 2_000_000_000
    answer(student, path, "second", "second")
    assert send(teacher, path + "/close").status_code == 200
    view = teacher.get(path + "/view").json
    assert view["questions"][0]["ranking"][0]["received_at"] == "2026-11-18T10:32:05.456+08:00"


def test_teacher_live_submissions_follow_effective_received_order(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    app.extensions["event_order"].clock = lambda: 100
    assert answer(other, path, "B first", "b1").status_code == 200
    assert answer(student, path, "A second", "a1").status_code == 200

    def groups():
        return [row["group"] for row in teacher.get(path + "/view").json["questions"][0]["submissions"]]

    assert groups() == [b["id"], a["id"]]
    app.extensions["event_order"].clock = lambda: 200
    assert answer(other, path, "B revised", "b2").status_code == 200
    assert groups() == [a["id"], b["id"]]


def test_first_place_is_final_and_judgment_api_is_removed(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    answer(student, path, "first possibly wrong", "a1")
    answer(other, path, "second possibly right", "b1")
    send(teacher, path + "/close")
    endpoint = f"{path}/questions/Q1/judgments/{a['id']}"
    assert send(teacher, endpoint, {"correct": False}, method="PUT").status_code == 404
    question = other.get(path + "/view").json["questions"][0]
    assert question["winner"] == {"group": a["id"], "name": "A"}
    assert "correct_answer" not in question and "ranking" not in question
    assert "first possibly wrong" not in other.get(path + "/view").text
    assert send(teacher, path + "/close").status_code == 200


def test_cannot_reopen_and_can_start_another_new_activity(app, teacher, prepared):
    path, a, _, student, _ = setup_round(app, teacher, prepared)
    first = answer(student, path, "first", "a1").json
    assert send(teacher, path + "/close").status_code == 200
    for mode in ("continue", "restart"):
        assert send(teacher, path + "/open", {"mode": mode}).status_code == 409
    assert student.get(path + "/view").json["questions"][0]["mine"]["timestamp"] == first["timestamp"]
    new, *_ = create_notes(teacher, "Other")
    assert new != path
    assert send(teacher, new + "/open").status_code == 200
    assert teacher.get(path + "/view").json["phase"] == "closed"
