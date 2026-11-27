"""The optional progress panel is retired; the submission monitor remains."""
from conftest import send
from test_import_join import prepared
from test_ranking_review import answer, setup_round


def test_monitor_retains_answers_and_times_without_progress_controls(app, teacher, prepared):
    path, a, b, student, other = setup_round(app, teacher, prepared)
    answer(other, path, "B first", "b")
    answer(student, path, "A second", "a")
    rows = teacher.get(path + "/view").json["questions"][0]["submissions"]
    assert [r["group"] for r in rows] == [b["id"], a["id"]]
    assert all(r["received_at"].endswith("+08:00") for r in rows)
    page = teacher.get("/teacher").text
    script = teacher.get("/static/teacher.js").text
    assert "submission-progress" not in script and "missing-groups" not in script
    assert 'id="questions"' in page


def test_empty_question_has_no_fabricated_submissions(teacher, prepared):
    _, path, *_ = prepared
    assert teacher.get(path + "/view").json["questions"][0]["submissions"] == []
