"""Acceptance rules approved 2026-11-26; exercises real routes and SQLite."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import send
from test_import_join import FakeSheets, URL


def preview(teacher):
    return send(teacher, '/api/guided-notes/preview', {'url': URL, 'sheet': 0})


def create(teacher, name='Class'):
    result = preview(teacher)
    assert result.status_code == 200, result.json
    response = send(teacher, '/api/activities', {'name': name, 'preview': result.json['preview']})
    assert response.status_code == 201, response.json
    return f"/api/activities/{response.json['id']}"


@pytest.fixture
def core(app, teacher):
    sheets = FakeSheets()
    sheets.cells = dict(sheets.cells)
    sheets.writes = []
    def write(_, __, changes):
        sheets.writes.append(changes)
        for row, col, value in changes:
            if value is None:
                sheets.cells.pop((row, col), None)
            else:
                sheets.cells[row, col] = {'stringValue': value}
    sheets.write = write
    app.extensions['sheets'] = sheets
    return sheets


def configured(teacher):
    path = create(teacher)
    result = send(teacher, path + '/groups', {'count': 2}, method='PUT')
    assert result.status_code == 200, result.json
    return path, result.json['groups']


def student(app, path, group):
    client = app.test_client()
    assert send(client, path + '/join', {'group': group['id']}).status_code == 200
    return client


def submit(client, path, answer='answer', receipt='first', **extra):
    view = client.get(path + '/view?audience=student').json
    data = {'number': 'Q1', 'answer': answer, 'receipt': receipt,
            'group': view['group']['id'], 'membership_version': view['membership_version']}
    return send(client, path + '/answers', data | extra)


def confirm_export(teacher, path):
    result = send(teacher, path + '/export/preview')
    assert result.status_code == 200, result.json
    return send(teacher, path + '/export', {'preview': result.json['preview']})


def test_import_preview_does_not_create_until_confirmed(app, teacher, core):
    result = preview(teacher)
    assert result.status_code == 200
    assert result.json['questions'][0]['answer_cell'] == 'D1'
    assert teacher.get('/api/activities').json['activities'] == []
    assert send(teacher, '/api/activities', {'name': 'Missing preview'}).status_code == 400
    path = create(teacher)
    assert len(teacher.get(path + '/view').json['questions']) == 2
    assert not core.writes


def test_import_preview_rejects_changed_or_foreign_or_tampered_content(app, teacher, core):
    token = preview(teacher).json['preview']
    other = app.test_client()
    with teacher.session_transaction() as source, other.session_transaction() as target:
        target['teacher'] = True
        target['csrf'] = 'different-browser'
    assert send(other, '/api/activities', {'name': 'Other', 'preview': token}).status_code == 409
    assert send(teacher, '/api/activities', {'name': 'Bad', 'preview': token + 'x'}).status_code == 409
    core.cells[8, 0] = {'stringValue': 'Q4'}
    core.cells[8, 3] = {'stringValue': '{{Q4}}'}
    assert send(teacher, '/api/activities', {'name': 'Changed', 'preview': token}).status_code == 409
    assert teacher.get('/api/activities').json['activities'] == []


def test_batch_groups_validation_and_locked_after_join(app, teacher, core):
    path = create(teacher)
    for count in (0, 101, True, 1.5, '2'):
        assert send(teacher, path + '/groups', {'count': count}, method='PUT').status_code == 400
    groups = send(teacher, path + '/groups', {'count': 2}, method='PUT').json['groups']
    assert len(groups) == 2 and all('code' not in group for group in groups)
    student(app, path, groups[0])
    assert send(teacher, path + '/groups', {'count': 3}, method='PUT').status_code == 409
    assert len(teacher.get(path + '/groups').json['groups']) == 2


def test_batch_rebuild_stays_locked_after_joined_group_is_deleted(app, teacher, core):
    path, groups = configured(teacher)
    student(app, path, groups[0])
    assert send(teacher, path + f"/groups/{groups[0]['id']}", method='DELETE').status_code == 200
    result = send(teacher, path + '/groups', {'count': 3}, method='PUT')
    assert result.status_code == 409 and result.json['code'] == 'groups_in_use'
    assert [g['id'] for g in teacher.get(path + '/groups').json['groups']] == [groups[1]['id']]


def test_closed_is_final_and_first_place_wins_without_judgment(app, teacher, core):
    path, groups = configured(teacher)
    a, b = [student(app, path, group) for group in groups]
    assert send(teacher, path + '/open').status_code == 200
    submit(a, path, 'possibly incorrect')
    submit(b, path, 'possibly correct')
    assert send(teacher, path + '/close').status_code == 200
    view = teacher.get(path + '/view').json
    assert view['questions'][0]['winner']['group'] == groups[0]['id']
    assert view['can_export'] is True
    assert send(teacher, path + '/close').status_code == 200
    for mode in ('continue', 'restart'):
        assert send(teacher, path + '/open', {'mode': mode}).status_code == 409
    assert send(teacher, path + '/guided-notes', {'url': URL}).status_code == 404
    assert send(teacher, path, method='DELETE').status_code == 400
    assert send(teacher, path + f"/questions/Q1/judgments/{groups[0]['id']}", {'correct': False}, method='PUT').status_code == 404
    public = b.get(path + '/view?audience=student').json['questions'][0]
    assert public['winner'] == {'group': groups[0]['id'], 'name': groups[0]['name']}
    assert public['mine']['answer'] == 'possibly correct' and public['own_rank'] == 2
    assert 'possibly incorrect' not in b.get(path + '/view?audience=student').text
    assert 'correct_answer' not in public and 'ranking' not in public


def test_same_answer_does_not_update_and_clock_regression_does_not_reverse_order(app, teacher, core):
    path, groups = configured(teacher)
    a, b = [student(app, path, group) for group in groups]
    send(teacher, path + '/open')
    app.extensions['event_order'].clock = lambda: 200
    first = submit(a, path, 'A').json
    assert submit(a, path, ' A ', 'same').json['code'] == 'answer_unchanged'
    assert submit(a, path, 'A', 'first').json == first
    app.extensions['event_order'].clock = lambda: 100
    second = submit(b, path, 'B').json
    assert second['sequence'] == first['sequence'] + 1
    send(teacher, path + '/close')
    assert teacher.get(path + '/view').json['questions'][0]['winner']['group'] == groups[0]['id']
    assert submit(a, path, 'A', 'new-after-close').json['code'] == 'closed'


def test_switch_is_immediate_but_stale_tabs_and_aba_are_rejected(app, teacher, core):
    path, groups = configured(teacher)
    a = student(app, path, groups[0])
    teammate = student(app, path, groups[0])
    send(teacher, path + '/open')
    submit(a, path, 'original')
    assert send(a, path + '/join', {'group': groups[1]['id']}).status_code == 200
    assert submit(a, path, 'stale', 'stale', group=groups[0]['id'], membership_version=0).json['code'] == 'group_changed'
    assert teammate.get(path + '/view').json['questions'][0]['mine']['answer'] == 'original'
    assert send(a, path + '/join', {'group': groups[0]['id']}).status_code == 200
    assert submit(a, path, 'stale again', 'aba', membership_version=0).status_code == 409
    assert submit(a, path, 'fresh', 'fresh').status_code == 200
    assert send(a, path + '/transfer-requests', {'group': groups[1]['id']}).status_code == 404


def test_export_preview_cancel_confirm_and_original_cell_conflict(app, teacher, core):
    path, groups = configured(teacher)
    a = student(app, path, groups[0])
    send(teacher, path + '/open')
    submit(a, path, '=literal')
    send(teacher, path + '/close')
    result = send(teacher, path + '/export/preview')
    assert result.status_code == 200
    assert result.json['changes'][0] == {'number': 'Q1', 'cell': 'D1', 'before': '{{Q1}}', 'answer': '=literal'}
    assert not core.writes
    assert send(teacher, path + '/export').status_code == 400
    token = result.json['preview']
    core.cells[0, 3] = {'stringValue': 'manual edit'}
    assert send(teacher, path + '/export', {'preview': token}).status_code == 409
    assert not core.writes
    core.cells[0, 3] = {'stringValue': '{{Q1}}'}
    assert send(teacher, path + '/export', {'preview': token}).json['written'] == 1
    assert core.cells[0, 3] == {'stringValue': '=literal'}
    assert confirm_export(teacher, path).json['written'] == 0


def test_activity_url_and_retired_controls(teacher, core):
    path, _ = configured(teacher)
    activity = path.rsplit('/', 1)[1]
    page = teacher.get('/teacher/activities/' + activity)
    assert page.status_code == 200
    assert f'data-activity="{activity}"' in page.text
    for text in ('id="reopen-options"', 'id="transfer-requests"'):
        assert text not in page.text
    assert teacher.get('/teacher/activities/999999').status_code == 404


def test_concurrent_identical_answers_only_one_new_submission(app, teacher, core):
    path, groups = configured(teacher)
    students = [student(app, path, groups[0]) for _ in range(2)]
    send(teacher, path + '/open')
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(submit, client, path, 'same', str(index)) for index, client in enumerate(students)]
        assert sorted(future.result().status_code for future in futures) == [200, 409]
    with app.extensions['store'].read() as db:
        assert db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 1


def test_import_confirmation_retry_reuses_activity_but_new_preview_is_independent(teacher, core):
    token = preview(teacher).json['preview']
    data = {'name': 'Class', 'preview': token}
    first = send(teacher, '/api/activities', data).json
    assert send(teacher, '/api/activities', data).json == first
    second = create(teacher, 'Next class')
    assert second != f"/api/activities/{first['id']}"
    assert len(teacher.get('/api/activities').json['activities']) == 2


def preview_clock(monkeypatch):
    from flask import current_app
    from itsdangerous import TimestampSigner, URLSafeTimedSerializer
    from buzzer import previews
    clock = [1000]
    class PreviewSigner(TimestampSigner):
        def get_timestamp(self):
            return clock[0]
    monkeypatch.setattr(previews, 'signer', lambda kind: URLSafeTimedSerializer(
        current_app.secret_key, salt='buzzer-preview-' + kind, signer=PreviewSigner))
    return clock


@pytest.mark.parametrize('seconds, expected', [(1200, 201), (1201, 409)])
def test_import_preview_expiration_boundary(teacher, core, monkeypatch, seconds, expected):
    clock = preview_clock(monkeypatch)
    token = preview(teacher).json['preview']
    clock[0] = 1000 + seconds
    result = send(teacher, '/api/activities', {'name': 'Class', 'preview': token})
    assert result.status_code == expected
    assert len(teacher.get('/api/activities').json['activities']) == (1 if expected == 201 else 0)


def test_export_tokens_are_bound_to_session_activity_and_expiration(app, teacher, core, monkeypatch):
    path, groups = configured(teacher)
    other_path = create(teacher, 'Other')
    a = student(app, path, groups[0])
    send(teacher, path + '/open')
    submit(a, path, 'value')
    send(teacher, path + '/close')
    clock = preview_clock(monkeypatch)
    token = send(teacher, path + '/export/preview').json['preview']
    stranger = app.test_client()
    with stranger.session_transaction() as session:
        session['teacher'] = True
    assert send(stranger, path + '/export', {'preview': token}).status_code == 409
    assert send(teacher, other_path + '/export', {'preview': token}).status_code == 409
    clock[0] = 2201
    assert send(teacher, path + '/export', {'preview': token}).status_code == 409
    assert not core.writes


def test_student_cannot_preview_create_configure_or_export(app, teacher, core):
    path, groups = configured(teacher)
    a = student(app, path, groups[0])
    token = preview(teacher).json['preview']
    for route, data, method in [
        ('/api/guided-notes/inspect', {'url': URL}, 'POST'),
        ('/api/guided-notes/preview', {'url': URL}, 'POST'),
        ('/api/activities', {'name': 'forbidden', 'preview': token}, 'POST'),
        (path + '/groups', {'count': 3}, 'PUT'),
        (path + '/export/preview', {}, 'POST'),
        (path + '/export', {}, 'POST'),
    ]:
        assert send(a, route, data, method=method).status_code == 403


def test_new_sequence_is_durable_and_unchanged_request_allocates_nothing(app, teacher, core):
    from buzzer import create_app
    path, groups = configured(teacher)
    a = student(app, path, groups[0])
    send(teacher, path + '/open')
    first = submit(a, path, 'one').json
    assert submit(a, path, 'one', 'unchanged').status_code == 409
    restarted = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']})
    client = restarted.test_client()
    with a.session_transaction() as old, client.session_transaction() as new:
        new.update(old)
    second = submit(client, path, 'two', 'second').json
    assert second['sequence'] == first['sequence'] + 1


def test_real_legacy_schema_upgrade_adds_import_key_without_removing_rows(tmp_path):
    import sqlite3
    from buzzer.store import Store, SCHEMA
    path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO activities(id,name,phase) VALUES (9,'Legacy','closed')")
    Store(path)
    with Store(path).read() as db:
        row = db.execute('SELECT * FROM activities WHERE id=9').fetchone()
        assert row['name'] == 'Legacy' and row['phase'] == 'closed' and row['import_key'] is None
        assert db.execute("SELECT last_id FROM identifiers WHERE kind='activities'").fetchone()[0] == 9


@pytest.mark.parametrize('sheet', [True, -1, 2**31, '0'])
def test_preview_validates_sheet_identifier(teacher, core, sheet):
    response = send(teacher, '/api/guided-notes/preview', {'url': URL, 'sheet': sheet})
    assert response.status_code == 400 and response.json['code'] == 'invalid_sheet'
