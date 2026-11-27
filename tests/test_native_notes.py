import json

import pytest

from conftest import send
from test_import_join import FakeSheets, URL, create_notes
from test_ranking_review import join, answer
from test_export import send_export
from buzzer.guided_notes import parse_questions
from buzzer.sheets import Grid, SheetsError


def native_cells(rows):
    cells = {(3, 1): {'stringValue': '題號'}, (3, 2): {'stringValue': '題目'}, (3, 6): {'stringValue': '作答'}}
    for row, number, prompt, placeholder in rows:
        if number is not None:
            cells[row, 1] = {'numberValue': number}
        cells[row, 2] = {'stringValue': prompt}
        if placeholder:
            cells[row, 6] = {'stringValue': placeholder}
    return cells


GROUP = {'startRowIndex': 4, 'endRowIndex': 6, 'startColumnIndex': 1, 'endColumnIndex': 2}
HEADER = {'startRowIndex': 3, 'endRowIndex': 4, 'startColumnIndex': 6, 'endColumnIndex': 8}


def native_setup(app, teacher, cells, merges=()):
    fake = FakeSheets()
    fake.cells, fake.merges, fake.writes = cells, merges, []
    fake.read = lambda *_: Grid(dict(fake.cells), lambda r, c: (r, c) not in fake.protected, fake.merges)
    def write(_, __, changes):
        fake.writes.append(changes)
        for row, col, value in changes:
            if value is None:
                fake.cells.pop((row, col), None)
            else:
                fake.cells[row, col] = {'stringValue': value}
    fake.write = write
    app.extensions['sheets'] = fake
    path, a, b = create_notes(teacher)
    return fake, path, a, b


def test_native_single_import_prompt_anchor_and_original_blank(app, teacher):
    cells = native_cells([(4, 1, '處理器簡稱', None), (6, 2, '二進位', None)])
    fake, path, team, _ = native_setup(app, teacher, cells)
    assert teacher.get(path + '/view').json['questions'][0]['prompt'] == '處理器簡稱'
    send(teacher, path + '/open')
    answer(join(app, path, team), path, 'CPU', 'first')
    send(teacher, path + '/close')
    fake.cells[4, 2] = {'stringValue': '另一題'}
    assert send_export(teacher, path).status_code == 409
    assert not fake.writes
    fake.cells[4, 2] = {'stringValue': '處理器簡稱'}
    assert send_export(teacher, path).json == {'written': 1}
    assert fake.writes == [[(4, 6, 'CPU')]]
    assert (6, 6) not in fake.cells  # unanswered question remains blank


def test_native_grouped_imports_each_subquestion_and_prompts(app, teacher):
    cells = native_cells([(4, 1, '硬體', '（1）'), (5, None, '系統軟體', '（2）'),
                          (7, 2, '演算法', '（1）'), (8, None, '堆疊', '（2）'),
                          (10, 3, '二進位', None), (12, 4, '網路位址', None)])
    second = dict(GROUP, startRowIndex=7, endRowIndex=9)
    _, path, team, _ = native_setup(app, teacher, cells, (GROUP, second))
    expected = ['Q1.1', 'Q1.2', 'Q2.1', 'Q2.2', 'Q3', 'Q4']
    for client in (teacher, join(app, path, team)):
        questions = client.get(path + '/view').json['questions']
        assert [q['number'] for q in questions] == expected
        assert [q['prompt'] for q in questions] == ['硬體', '系統軟體', '演算法', '堆疊', '二進位', '網路位址']


@pytest.mark.parametrize('value', [{'numberValue': 1}, {'stringValue': '1'}])
def test_duplicate_native_numbers_rejected_with_cell(value):
    cells = native_cells([(4, 1, '第一題', None), (6, 2, '第二題', None)])
    cells[6, 1] = value
    with pytest.raises(SheetsError, match='B7'):
        parse_questions(Grid(cells, lambda *_: True))


@pytest.mark.parametrize('split', [False, True])
def test_grouped_export_preserves_labels_and_rejects_manual_changes(app, teacher, split):
    cells = native_cells([(4, 1, '硬體', '（1）'), (5, None, '軟體', '（2）')])
    fake, path, team, _ = native_setup(app, teacher, cells, (GROUP, HEADER) if split else (GROUP,))
    send(teacher, path + '/open')
    answer(join(app, path, team), path, 'CPU', 'first', 'Q1.1')
    send(teacher, path + '/close')
    target = (4, 7) if split else (4, 6)
    original = fake.cells.get(target)
    fake.cells[target] = {'stringValue': '人工備註'}
    assert send_export(teacher, path).status_code == 409
    assert not fake.writes
    if original:
        fake.cells[target] = original
    else:
        fake.cells.pop(target)
    assert send_export(teacher, path).json == {'written': 1}
    assert fake.cells[4, 6] == {'stringValue': '（1）' if split else '（1）CPU'}
    if split:
        assert fake.cells[4, 7] == {'stringValue': 'CPU'}
    assert fake.cells[5, 6] == {'stringValue': '（2）'}
    assert fake.cells[4, 1] == {'numberValue': 1}
    assert send_export(teacher, path).json == {'written': 0}


def test_legacy_split_answer_mapping_migrates_without_overwriting_label(app, teacher):
    cells = native_cells([(4, 1, '硬體', '（1）'), (5, None, '軟體', '（2）')])
    fake, path, team, _ = native_setup(app, teacher, cells, (GROUP,))
    send(teacher, path + '/open')
    answer(join(app, path, team), path, 'CPU', 'first', 'Q1.1')
    send(teacher, path + '/close')
    assert send_export(teacher, path).status_code == 200
    fake.merges = (GROUP, HEADER)
    fake.cells[4, 7] = {'stringValue': '人工備註'}
    assert send_export(teacher, path).status_code == 409
    fake.cells.pop((4, 7))
    assert send_export(teacher, path).json['written'] == 2
    assert fake.cells[4, 6] == {'stringValue': '（1）'}
    assert fake.cells[4, 7] == {'stringValue': 'CPU'}


@pytest.mark.parametrize('kind', ['missing', 'answered', 'protected'])
def test_native_invalid_prompt_answer_or_permissions(kind):
    cells = native_cells([(4, 1, '第一題', None)])
    if kind == 'missing':
        cells.pop((4, 2))
    if kind == 'answered':
        cells[4, 6] = {'stringValue': '已有答案'}
    with pytest.raises(SheetsError):
        parse_questions(Grid(cells, lambda *_: kind != 'protected'))
