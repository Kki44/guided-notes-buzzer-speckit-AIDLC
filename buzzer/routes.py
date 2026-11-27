import json
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, render_template, request, session
from werkzeug.exceptions import HTTPException

from .access import csrf_token, matches
from .guided_notes import cell_name, export_notes, parse_questions, prepare_export, spreadsheet_id
from .previews import digest, sign, verify
from .review import lock_rankings, outcome, ranking_for
from .sheets import SheetsError
from .submissions import prior_receipt, save_submission, submissions_for


api = Blueprint("buzzer", __name__)


class Problem(Exception):
    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message


@api.errorhandler(Problem)
def handle_problem(error):
    return {"code": error.code, "message": error.message}, error.status


@api.errorhandler(HTTPException)
def handle_http(error):
    return {"code": "invalid_request", "message": "請確認請求格式與大小。"}, error.code


@api.errorhandler(SheetsError)
def handle_sheets(error):
    return {"code": "sheets_error", "message": error.message}, error.status


@api.before_request
def verify_write():
    if request.method not in {"POST", "PUT", "DELETE"}:
        return
    origin = request.headers.get("Origin")
    token = request.headers.get("X-CSRF-Token", "")
    if (origin and origin != request.host_url.rstrip("/")) or not session.get("csrf") or not matches(token, session["csrf"]):
        raise Problem(403, "csrf", "操作驗證失敗，請重新載入頁面。")


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise Problem(400, "invalid_request", "請提供 JSON 資料。")
    return data


def field(data, name, label, limit=200, *, strip=True):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Problem(400, "invalid_input", f"請輸入有效的{label}（最多 {limit} 字）。")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise Problem(400, "invalid_input", f"{label}包含無效文字。") from None
    return value.strip() if strip else value


@api.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


def require_teacher():
    if not session.get("teacher"):
        raise Problem(403, "teacher_required", "此操作需要老師身分。")


def store():
    return current_app.extensions["store"]


def next_id(db, table):
    return db.execute(
        "UPDATE identifiers SET last_id = last_id + 1 WHERE kind = ? RETURNING last_id", (table,),
    ).fetchone()[0]


def get_activity(db, activity):
    if activity >= 2**63:
        raise Problem(404, "activity_missing", "找不到活動。")
    row = db.execute("SELECT * FROM activities WHERE id = ?", (activity,)).fetchone()
    if row is None:
        raise Problem(404, "activity_missing", "找不到活動。")
    return row


def membership(db, activity):
    return db.execute(
        "SELECT team, version FROM memberships WHERE browser = ? AND activity = ?",
        (session.get("csrf"), activity),
    ).fetchone()


@api.get("/")
def student_page():
    return render_template("student.html", csrf=csrf_token())


@api.get("/teacher")
@api.get("/teacher/activities/<int:activity>")
def teacher_page(activity=None):
    if activity is not None:
        with store().read() as db:
            get_activity(db, activity)
    return render_template("teacher.html", csrf=csrf_token(), logged_in=bool(session.get("teacher")), activity=activity)


@api.post("/api/teacher/session")
def teacher_session():
    password = field(payload(), "password", "管理密碼", 4096, strip=False)
    if not matches(password, current_app.config["TEACHER_PASSWORD"]):
        raise Problem(401, "password_invalid", "管理密碼不正確。")
    session["teacher"] = True
    return {"ok": True}


@api.get("/api/activities")
def list_activities():
    with store().read() as db:
        rows = db.execute("SELECT id, name, phase FROM activities ORDER BY id DESC")
        return {"activities": [dict(row) for row in rows]}


def read_import(data):
    spreadsheet = spreadsheet_id(field(data, "url", "試算表連結", 2048))
    sheet = data.get("sheet")
    if sheet is not None and (type(sheet) is not int or not 0 <= sheet < 2**31):
        raise Problem(400, "invalid_sheet", "請選擇有效的工作表。")
    sheets = current_app.extensions["sheets"]
    choices = sheets.inspect(spreadsheet)
    if sheet is None:
        if len(choices) != 1:
            raise Problem(400, "choose_sheet", "請先讀取工作表，再選擇要匯入的工作表。")
        sheet = choices[0]["id"]
    if not any(choice["id"] == sheet for choice in choices):
        raise Problem(400, "sheet_missing", "找不到所選工作表。")
    questions = parse_questions(sheets.read(spreadsheet, sheet))
    return spreadsheet, sheet, questions


@api.post("/api/guided-notes/inspect")
def inspect_notes():
    require_teacher()
    spreadsheet = spreadsheet_id(field(payload(), "url", "試算表連結", 2048))
    return {"sheets": current_app.extensions["sheets"].inspect(spreadsheet)}


@api.post("/api/guided-notes/preview")
def preview_notes():
    require_teacher()
    spreadsheet, sheet, questions = read_import(payload())
    token = sign("import", {"spreadsheet": spreadsheet, "sheet": sheet, "digest": digest(questions), "nonce": uuid4().hex})
    return {"preview": token, "sheet": sheet, "questions": [
        {"number": row[0], "answer_cell": cell_name(row[3], row[4]),
         "prompt": json.loads(row[6])["anchors"][1][1].get("stringValue") if row[6] else None}
        for row in questions
    ]}


@api.post("/api/activities")
def create_activity():
    require_teacher()
    data = payload()
    name = field(data, "name", "活動名稱")
    token = data.get("preview")
    preview = verify("import", token)
    key = digest(token)
    with store().read() as db:
        existing = db.execute("SELECT id, name, phase FROM activities WHERE import_key = ?", (key,)).fetchone()
        if existing:
            return dict(existing), 201
    spreadsheet, sheet, questions = read_import({
        "url": f"https://docs.google.com/spreadsheets/d/{preview['spreadsheet']}/edit", "sheet": preview['sheet'],
    })
    if digest(questions) != preview["digest"]:
        raise Problem(409, "preview_changed", "工作表內容已變更，請重新預覽後確認。")
    with store().transaction() as db:
        existing = db.execute("SELECT id, name, phase FROM activities WHERE import_key = ?", (key,)).fetchone()
        if existing:
            return dict(existing), 201
        activity = next_id(db, "activities")
        db.execute("INSERT INTO activities(id,name,spreadsheet,sheet,worksheet_version,import_key) VALUES (?,?,?,?,1,?)",
                   (activity, name, spreadsheet, sheet, key))
        db.executemany(
            "INSERT INTO questions(activity,number,label_row,label_col,answer_row,answer_col,marker,source) VALUES (?,?,?,?,?,?,?,?)",
            [(activity, *question) for question in questions],
        )
    return {"id": activity, "name": name, "phase": "ready"}, 201


@api.delete("/api/activities/<int:activity>")
def delete_activity(activity):
    require_teacher()
    if payload().get("confirm") is not True:
        raise Problem(400, "confirmation_required", "請先確認永久刪除此活動及所有相關作答資料。")
    with current_app.extensions["event_order"].receive(), current_app.extensions["export_lock"], store().transaction() as db:
        if get_activity(db, activity)["phase"] == "open":
            raise Problem(409, "activity_open", "請先結束搶答，再刪除活動。")
        if db.execute("SELECT 1 FROM export_batches WHERE activity = ?", (activity,)).fetchone():
            raise Problem(409, "export_pending", "上次回填結果尚待核對，請先預覽回填以核對結果，再刪除活動。")
        for table in ("rankings", "exports", "submissions"):
            db.execute(f"DELETE FROM {table} WHERE question IN (SELECT id FROM questions WHERE activity = ?)", (activity,))
        for table in ("receipts", "transfer_requests", "round_history", "memberships", "questions", "groups"):
            db.execute(f"DELETE FROM {table} WHERE activity = ?", (activity,))
        db.execute("DELETE FROM activities WHERE id = ?", (activity,))
    return {"deleted": True}


def require_ready(db, activity):
    if get_activity(db, activity)["phase"] != "ready":
        raise Problem(409, "settings_locked", "只有準備中的活動可以更改組別。")


@api.post("/api/activities/<int:activity>/groups")
def create_group(activity):
    require_teacher()
    name = field(payload(), "name", "組別名稱")
    with store().transaction() as db:
        require_ready(db, activity)
        if db.execute("SELECT 1 FROM groups WHERE activity = ? AND name = ?", (activity, name)).fetchone():
            raise Problem(409, "duplicate_group", "這個組別名稱已使用。")
        group = next_id(db, "groups")
        db.execute("INSERT INTO groups(id, activity, name) VALUES (?,?,?)", (group, activity, name))
    return {"id": group, "name": name}, 201


@api.put("/api/activities/<int:activity>/groups")
def replace_groups(activity):
    require_teacher()
    count = payload().get("count")
    if type(count) is not int or not 1 <= count <= 100:
        raise Problem(400, "invalid_count", "組別數量必須是 1 至 100 的整數。")
    with store().transaction() as db:
        require_ready(db, activity)
        if get_activity(db, activity)["joined_once"]:
            raise Problem(409, "groups_in_use", "已有學生加入，無法整批重建組別。")
        # Old requests remain preserved; they must not be destroyed by rebuilding.
        if db.execute("SELECT 1 FROM transfer_requests WHERE activity = ?", (activity,)).fetchone():
            raise Problem(409, "groups_in_use", "此活動有舊組別紀錄，請逐組調整或建立新活動。")
        db.execute("DELETE FROM groups WHERE activity = ?", (activity,))
        groups = [{"id": next_id(db, "groups"), "name": f"第 {i + 1} 組"} for i in range(count)]
        db.executemany("INSERT INTO groups(id,activity,name) VALUES (?,?,?)",
                       [(g["id"], activity, g["name"]) for g in groups])
        db.execute("UPDATE activities SET revision = revision + 1 WHERE id = ?", (activity,))
    return {"groups": groups}


@api.delete("/api/activities/<int:activity>/groups/<int:team>")
def delete_group(activity, team):
    require_teacher()
    with store().transaction() as db:
        require_ready(db, activity)
        if team >= 2**63 or not db.execute("SELECT 1 FROM groups WHERE id = ? AND activity = ?", (team, activity)).fetchone():
            raise Problem(404, "group_missing", "找不到所選組別。")
        if db.execute("SELECT 1 FROM submissions WHERE team = ?", (team,)).fetchone() or db.execute(
            "SELECT 1 FROM transfer_requests WHERE source = ? OR target = ?", (team, team),
        ).fetchone():
            raise Problem(409, "group_history", "此組有既有作答或申請紀錄，為保留資料無法刪除。")
        db.execute("DELETE FROM memberships WHERE team = ?", (team,))
        db.execute("DELETE FROM groups WHERE id = ?", (team,))
        db.execute("UPDATE activities SET revision = revision + 1 WHERE id = ?", (activity,))
    return {"deleted": True}


@api.get("/api/activities/<int:activity>/groups")
def list_groups(activity):
    with store().read() as db:
        get_activity(db, activity)
        groups = [dict(row) for row in db.execute(
            "SELECT id, name FROM groups WHERE activity = ? ORDER BY id", (activity,),
        )]
        joined = membership(db, activity)
    return {"groups": groups, "joined": joined["team"] if joined else None}


@api.post("/api/activities/<int:activity>/join")
def join_group(activity):
    team = payload().get("group")
    if type(team) is not int or not 0 < team < 2**63:
        raise Problem(400, "invalid_group", "請選擇有效的組別。")
    with store().transaction() as db:
        get_activity(db, activity)
        if not db.execute("SELECT 1 FROM groups WHERE activity = ? AND id = ?", (activity, team)).fetchone():
            raise Problem(404, "group_missing", "找不到所選組別。")
        joined = membership(db, activity)
        if joined and joined["team"] != team:
            db.execute("UPDATE memberships SET team = ?, version = version + 1 WHERE browser = ? AND activity = ?",
                       (team, session["csrf"], activity))
            db.execute("DELETE FROM receipts WHERE activity = ? AND browser = ?", (activity, session["csrf"]))
        elif not joined:
            db.execute("INSERT INTO memberships(browser,activity,team) VALUES (?,?,?)", (session["csrf"], activity, team))
        db.execute("UPDATE activities SET joined_once = 1 WHERE id = ?", (activity,))
        version = membership(db, activity)["version"]
    return {"group": team, "membership_version": version}


@api.post("/api/activities/<int:activity>/open")
def open_activity(activity):
    require_teacher()
    with current_app.extensions["event_order"].receive(), store().transaction() as db:
        if get_activity(db, activity)["phase"] != "ready":
            raise Problem(409, "settings_locked", "只有準備中的活動可開放；已結束活動不能重新開放。")
        if db.execute("SELECT 1 FROM activities WHERE phase = 'open'").fetchone():
            raise Problem(409, "another_open", "已有一場搶答開放中。")
        count = db.execute("SELECT COUNT(*) FROM groups WHERE activity = ?", (activity,)).fetchone()[0]
        if count < 2 or not db.execute("SELECT 1 FROM questions WHERE activity = ?", (activity,)).fetchone():
            raise Problem(409, "not_ready", "請先準備至少一題與兩個組別。")
        db.execute("UPDATE activities SET phase = 'open', revision = revision + 1 WHERE id = ?", (activity,))
    return {"phase": "open"}


def get_question(db, activity, number):
    row = db.execute("SELECT id FROM questions WHERE activity = ? AND number = ?", (activity, number)).fetchone()
    if not row:
        raise Problem(404, "question_missing", "找不到這個題號。")
    return row["id"]


@api.post("/api/activities/<int:activity>/answers")
def submit_answer(activity):
    with current_app.extensions["event_order"].receive() as received, store().transaction() as db:
        activity_row = get_activity(db, activity)
        phase = activity_row["phase"]
        joined = membership(db, activity)
        if not joined:
            raise Problem(403, "group_required", "請先加入組別。")
        data = payload()
        membership_version = data.get("membership_version", 0)
        if type(membership_version) is not int or membership_version != joined["version"]:
            raise Problem(409, "group_changed", "你的組別已變更，請重新載入頁面並確認答案後再提交。")
        if "group" in data and (type(data["group"]) is not int or data["group"] != joined["team"]):
            raise Problem(409, "group_changed", "你的組別已變更，請確認新組別及答案後再提交。")
        if "worksheet_version" in data:
            version = data["worksheet_version"]
            if type(version) is not int or version != activity_row["worksheet_version"]:
                raise Problem(409, "worksheet_changed", "學習單版本已變更，請更新題目後再提交。")
        receipt = field(data, "receipt", "送出識別", 100)
        number = field(data, "number", "題號")
        answer = field(data, "answer", "答案", 4000)
        browser = session["csrf"]
        prior = prior_receipt(db, activity, browser, receipt)
        if prior:
            if (prior["number"], prior["answer"]) != (number, answer):
                raise Problem(409, "receipt_conflict", "同一次送出識別的內容不同，請重新提交。")
            return json.loads(prior["response"])
        if phase == "closed":
            raise Problem(409, "closed", "搶答已結束。")
        if phase != "open":
            raise Problem(409, "not_open", "搶答尚未開放。")
        question = get_question(db, activity, number)
        previous = db.execute("SELECT answer FROM submissions WHERE question = ? AND team = ?",
                              (question, joined["team"])).fetchone()
        if previous and previous["answer"] == answer:
            raise Problem(409, "answer_unchanged", "答案未變更，無須重新提交")
        received = (received[0], next_id(db, "submissions"))
        db.execute("UPDATE activities SET revision = revision + 1 WHERE id = ?", (activity,))
        return save_submission(db, activity, browser, joined["team"], question, number, answer, receipt, received)


@api.post("/api/activities/<int:activity>/close")
def close_activity(activity):
    require_teacher()
    with current_app.extensions["event_order"].receive(), store().transaction() as db:
        phase = get_activity(db, activity)["phase"]
        if phase == "closed":
            return {"phase": "closed"}
        if phase != "open":
            raise Problem(409, "not_open", "只能結束開放中的活動。")
        lock_rankings(db, activity)
        db.execute("UPDATE activities SET phase = 'closed', revision = revision + 1 WHERE id = ?", (activity,))
    return {"phase": "closed"}


@api.get("/api/activities/<int:activity>/view")
def activity_view(activity):
    audience = request.args.get("audience")
    if audience not in (None, "teacher", "student"):
        raise Problem(400, "invalid_audience", "請選擇老師或學生檢視。")
    if audience == "teacher":
        require_teacher()
    teacher = bool(session.get("teacher")) and audience != "student"
    with store().read() as db:
        db.execute("BEGIN")
        row = get_activity(db, activity)
        joined = membership(db, activity)
        if not teacher and not joined:
            raise Problem(403, "group_required", "請先加入組別。")
        questions = []
        for question in db.execute(
            "SELECT id, number, source FROM questions WHERE activity = ? ORDER BY id", (activity,),
        ):
            source = json.loads(question["source"]) if question["source"] else None
            prompt = source["anchors"][1][1].get("stringValue") if source else None
            data = {"number": question["number"], "prompt": prompt}
            submissions = submissions_for(db, question["id"])
            if teacher:
                data["submissions"] = [teacher_submission(item) for item in submissions]
            else:
                data["mine"] = next((dict(item) for item in submissions if item["group"] == joined["team"]), None)
            if row["phase"] == "closed":
                ranking = ranking_for(db, question["id"])
                data["status"], winner = outcome(ranking)
                if teacher:
                    data["winner"] = winner
                    data["ranking"] = [teacher_submission(item) for item in ranking]
                else:
                    data["own_rank"] = next(
                        (item["rank"] for item in ranking if item["group"] == joined["team"]), None,
                    )
                    data["winner"] = {key: winner[key] for key in ("group", "name")} if winner else None
            questions.append(data)
        view = {"phase": row["phase"], "name": row["name"], "questions": questions,
                "worksheet_version": row["worksheet_version"]}
        view["groups"] = [dict(item) for item in db.execute(
            "SELECT id, name FROM groups WHERE activity = ? ORDER BY id", (activity,),
        )]
        if teacher:
            view["can_export"] = row["phase"] == "closed"
            view["groups_locked"] = bool(row["joined_once"])
        else:
            group = db.execute("SELECT id, name FROM groups WHERE id = ?", (joined["team"],)).fetchone()
            view["group"] = dict(group)
            view["membership_version"] = joined["version"]

        return view


def teacher_submission(row):
    data = dict(row)
    seconds, nanos = divmod(row["timestamp"], 1_000_000_000)
    received = datetime.fromtimestamp(seconds, timezone(timedelta(hours=8)))
    data["received_at"] = received.replace(microsecond=nanos // 1000).isoformat(timespec="milliseconds")
    return data


def export_activity_row(activity):
    with store().read() as db:
        row = get_activity(db, activity)
    if row["phase"] != "closed":
        raise Problem(409, "not_closed", "請先結束搶答再預覽回填。")
    return row


@api.post("/api/activities/<int:activity>/export/preview")
def preview_export(activity):
    require_teacher()
    with current_app.extensions["export_lock"]:
        row = export_activity_row(activity)
        changes = prepare_export(store(), current_app.extensions["sheets"], row)
        token = sign("export", {"activity": activity, "revision": row["revision"], "digest": digest(changes)})
        return {"preview": token, "spreadsheet": row["spreadsheet"], "sheet": row["sheet"],
                "warning": "搶答成功答案未經正確性判定；確認後才會寫入，請暫停共同編輯原表。",
                "changes": [{"number": c["number"], "cell": cell_name(*c["cell"]),
                             "before": c["expected"], "answer": c["desired"]} for c in changes]}


@api.post("/api/activities/<int:activity>/export")
def export_activity(activity):
    require_teacher()
    preview = verify("export", payload().get("preview"))
    with current_app.extensions["export_lock"]:
        row = export_activity_row(activity)
        if preview.get("activity") != activity or preview.get("revision") != row["revision"]:
            raise Problem(409, "preview_changed", "活動已變更，請重新預覽回填。")
        return {"written": export_notes(store(), current_app.extensions["sheets"], row, expected_digest=preview["digest"])}
