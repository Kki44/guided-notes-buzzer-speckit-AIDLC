import json
from conftest import send
from test_import_join import prepared
from test_ranking_review import join, answer, setup_round


def test_delete_group_is_ready_only_and_members_must_rejoin(app, teacher, prepared):
    _, path, a, b = prepared
    student = join(app, path, a)
    group = f"{path}/groups/{a['id']}"
    assert send(student, group, method="DELETE").status_code == 403
    assert teacher.delete(group).status_code == 403
    assert send(teacher, group, method="DELETE").status_code == 200
    assert student.get(path + "/view").status_code == 403
    assert send(student, path + "/join", {"group": a["id"]}).status_code == 404
    assert send(teacher, group, method="DELETE").status_code == 404
    send(teacher, path + "/groups", {"name": "C"})
    assert send(teacher, path + "/open").status_code == 200
    assert send(teacher, f"{path}/groups/{b['id']}", method="DELETE").status_code == 409
    send(teacher, path + "/close")
    assert send(teacher, f"{path}/groups/{b['id']}", method="DELETE").status_code == 409
    assert send(teacher, path, {"confirm": True}, method="DELETE").status_code == 200


def test_upgrade_preserves_old_judgments_transfers_history_and_uses_first_place(app, teacher, prepared):
    from buzzer.store import Store
    path, a, b, student, other = setup_round(app, teacher, prepared)
    answer(student, path, "first", "a")
    answer(other, path, "second", "b")
    send(teacher, path + "/close")
    activity = int(path.rsplit("/", 1)[1])
    with student.session_transaction() as session:
        browser = session["csrf"]
    snapshot = {"questions": [{"number": "Q1", "ranking": [{"rank": 1, "answer": "legacy", "name": "A", "correct": 0}]}]}
    with app.extensions["store"].transaction() as db:
        db.execute("UPDATE rankings SET correct = CASE WHEN team = ? THEN 0 ELSE 1 END", (a["id"],))
        db.execute("INSERT INTO round_history(activity,snapshot) VALUES (?,?)", (activity, json.dumps(snapshot)))
        db.execute("INSERT INTO transfer_requests(activity,browser,source,target) VALUES (?,?,?,?)", (activity, browser, a["id"], b["id"]))
    Store(app.config["DATABASE"])
    assert teacher.get(path + "/view").json["questions"][0]["winner"]["group"] == a["id"]
    assert teacher.get(path + "/history").status_code == 404
    assert student.get(path + "/history").status_code == 404
    with app.extensions["store"].read() as db:
        assert json.loads(db.execute("SELECT snapshot FROM round_history WHERE activity = ?", (activity,)).fetchone()[0]) == snapshot
        assert db.execute("SELECT COUNT(*) FROM transfer_requests").fetchone()[0] == 1
        assert [r[0] for r in db.execute("SELECT correct FROM rankings ORDER BY rank")] == [0, 1]


def test_teacher_page_has_no_old_rounds_panel_or_fetch(teacher, prepared):
    _, path, *_ = prepared
    for url in ('/teacher', '/teacher/activities/' + path.rsplit('/', 1)[1]):
        page = teacher.get(url)
        assert page.status_code == 200
        assert 'id="round-history"' not in page.text
        assert 'id="history-content"' not in page.text
        assert '舊輪次資料' not in page.text
    assert teacher.get(path + '/history').status_code == 404
    script = teacher.get('/static/teacher.js').text
    assert 'refreshHistory' not in script
    assert 'history.replaceState' in script  # Activity URLs still work.


def test_delete_activity_validates_role_confirmation_phase_and_pending(app, teacher, prepared):
    _, path, a, _ = prepared
    student = join(app, path, a)
    assert send(student, path, {"confirm": True}, method="DELETE").status_code == 403
    assert teacher.delete(path).status_code == 403
    assert send(teacher, path, method="DELETE").status_code == 400
    assert send(teacher, path, {"confirm": "true"}, method="DELETE").status_code == 400
    send(teacher, path + "/open")
    assert send(teacher, path, {"confirm": True}, method="DELETE").status_code == 409
    send(teacher, path + "/close")
    with app.extensions["store"].transaction() as db:
        db.execute("INSERT INTO export_batches VALUES (?, 'pending', 0, 0, '[]')", (int(path.rsplit('/',1)[1]),))
    assert send(teacher, path, {"confirm": True}, method="DELETE").json["code"] == "export_pending"
    assert teacher.get(path + '/view').status_code == 200


def test_delete_closed_activity_removes_related_rows_only(app, teacher, prepared):
    from test_import_join import create_notes
    path, a, b, student, other = setup_round(app, teacher, prepared)
    answer(student, path, 'saved', 'first')
    send(teacher, path + '/close')
    activity = int(path.rsplit('/',1)[1])
    with student.session_transaction() as session:
        browser = session['csrf']
    with app.extensions['store'].transaction() as db:
        db.execute("INSERT INTO exports SELECT id, 'saved', 0 FROM questions WHERE activity=? AND number='Q1'", (activity,))
        db.execute("INSERT INTO round_history(activity,snapshot) VALUES (?, '{}')", (activity,))
        db.execute("INSERT INTO transfer_requests(activity,browser,source,target) VALUES (?,?,?,?)", (activity,browser,a['id'],b['id']))
    new, *_ = create_notes(teacher, 'Other')
    assert send(teacher, path, {'confirm': True}, method='DELETE').status_code == 200
    assert teacher.get(path + '/view').status_code == 404
    assert student.get(path + '/view').status_code == 404
    assert teacher.get(new + '/view').status_code == 200
    with app.extensions['store'].read() as db:
        for table in ('submissions','receipts','rankings','exports','round_history','transfer_requests','memberships'):
            assert db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] == 0
    assert send(teacher, path, {'confirm': True}, method='DELETE').status_code == 404
