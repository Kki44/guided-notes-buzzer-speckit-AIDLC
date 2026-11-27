from concurrent.futures import ThreadPoolExecutor

from conftest import send
from test_import_join import prepared
from test_ranking_review import join, answer


def test_eight_groups_submit_together_and_only_teammates_see_answers(app, teacher, prepared):
    _, path, first, second = prepared
    groups = [first, second]
    for index in range(3, 9):
        groups.append(send(teacher, path + "/groups", {"name": f"G{index}"}).json)
    clients = [join(app, path, group) for group in groups]
    teammates = [join(app, path, group) for group in groups]
    assert send(teacher, path + "/open").status_code == 200

    def submit(index):
        question = "Q1" if index % 2 == 0 else "Q3"
        return answer(clients[index], path, f"answer-{index}", "first", question)

    with ThreadPoolExecutor(8) as executor:
        assert all(response.status_code == 200 for response in executor.map(submit, range(8)))

    for index, teammate in enumerate(teammates):
        view = teammate.get(path + "/view").json
        mine = [question["mine"] for question in view["questions"] if question["mine"]]
        assert [item["answer"] for item in mine] == [f"answer-{index}"]
        assert all("ranking" not in question and "submissions" not in question for question in view["questions"])
    view = teacher.get(path + "/view").json
    assert sum(len(question["submissions"]) for question in view["questions"]) == 8
    assert answer(teammates[0], path, "revised-by-teammate", "second").status_code == 200
    assert clients[0].get(path + "/view").json["questions"][0]["mine"]["answer"] == "revised-by-teammate"
    assert send(teacher, path + "/close").status_code == 200
    for client in clients:
        assert client.get(path + "/view").json["phase"] == "closed"
        assert answer(client, path, "late", "late").status_code == 409
