import json
import re
from urllib.parse import urlsplit

from .sheets import SheetsError, contains
from .previews import digest
from .review import outcome, ranking_for


NUMBER = re.compile(r"Q[1-9][0-9]*")
MARKER = re.compile(r"\{\{(Q[1-9][0-9]*)\}\}")


def spreadsheet_id(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        parts = None
    match = re.fullmatch(r"/spreadsheets/d/([\w-]+)(?:/[^/]+)?/?", parts.path, re.ASCII) if parts else None
    if not match or parts.scheme != "https" or parts.netloc.lower() != "docs.google.com":
        raise SheetsError("請輸入有效的 Google Sheets 連結。", 400)
    return match[1]


def cell_name(row, col):
    letters = ""
    col += 1
    while col:
        col, digit = divmod(col - 1, 26)
        letters = chr(65 + digit) + letters
    return f"{letters}{row + 1}"


def parse_questions(grid):
    if any(
        NUMBER.fullmatch(cell.get("stringValue", "")) or MARKER.fullmatch(cell.get("stringValue", ""))
        for cell in grid.cells.values()
    ):
        return parse_marked_questions(grid)
    return parse_native_questions(grid)


def parse_marked_questions(grid):
    labels, markers = {}, {}
    for point, cell in grid.cells.items():
        value = cell.get("stringValue", "")
        marker = MARKER.fullmatch(value)
        if marker:
            target, number = markers, marker[1]
        elif NUMBER.fullmatch(value):
            target, number = labels, value
        else:
            continue
        if number in target:
            old = cell_name(*target[number])
            new = cell_name(*point)
            raise SheetsError(f"{number} 標記重複：{old}、{new}。", 400)
        target[number] = point
    if not labels and not markers:
        raise SheetsError("找不到題號與答案格標記。", 400)
    for number in sorted(labels.keys() ^ markers.keys()):
        point = labels.get(number) or markers[number]
        raise SheetsError(f"{number} 的題號與答案格未配對（{cell_name(*point)}）。", 400)
    result = []
    for number, label in sorted(labels.items(), key=lambda item: (len(item[0]), item[0])):
        answer = markers[number]
        if not grid.editable(*answer):
            raise SheetsError(f"{number} 的答案格 {cell_name(*answer)} 無法編輯。", 403)
        result.append((number, *label, *answer, "{{" + number + "}}", None))
    return result


def native_columns(cells):
    by_row = {}
    for (row, col), cell in cells.items():
        value = cell.get("stringValue", "").strip()
        if value in {"題號", "題目", "作答"}:
            by_row.setdefault(row, {}).setdefault(value, []).append(col)
    headers = [
        (row, columns) for row, columns in by_row.items()
        if set(columns) == {"題號", "題目", "作答"}
    ]
    if len(headers) != 1 or any(len(cols) != 1 for cols in headers[0][1].values()):
        raise SheetsError("找不到唯一的「題號／題目／作答」表頭。請選擇教授範本格式的工作表。", 400)
    row, columns = headers[0]
    return row, *(columns[label][0] for label in ("題號", "題目", "作答"))


def native_number(cell):
    value = cell.get("numberValue")
    if isinstance(value, (int, float)) and 0 < value <= 999999999 and value == int(value):
        return str(int(value))
    text = cell.get("stringValue", "").strip()
    return text if re.fullmatch(r"[1-9][0-9]{0,8}", text) else None


def adjacent_answer_cell(grid, header, label):
    row, col = label
    answer = (row, col + 1)
    if any(contains(area, header, col) and contains(area, header, col + 1) for area in grid.merges):
        if not any(contains(area, *answer) and contains(area, *label) for area in grid.merges):
            return answer
    return label


def parse_native_questions(grid):
    cells = grid.cells
    header, label_col, prompt_col, answer_col = native_columns(cells)
    groups = {
        merge["startRowIndex"]: merge["endRowIndex"]
        for merge in grid.merges
        if merge.get("startColumnIndex", 0) == label_col and merge.get("endColumnIndex") == label_col + 1
        and merge.get("startRowIndex", 0) > header
        and merge["endRowIndex"] > merge["startRowIndex"] + 1
    }
    result, seen, group_rows = [], set(), set()
    for row in sorted({row for row, col in cells if col in (label_col, prompt_col) and row > header}):
        if row in group_rows:
            continue
        label = (row, label_col)
        label_value = cells.get(label, {})
        number = native_number(label_value)
        if number is None:
            if (row, prompt_col) in cells:
                raise SheetsError(f"{cell_name(*label)} 缺少有效題號。", 400)
            continue
        if number in seen:
            raise SheetsError(f"題號 {number} 重複（{cell_name(*label)}）。", 400)
        seen.add(number)
        end = groups.get(row, row + 1)
        group_rows.update(range(row + 1, end))
        for child in range(row, end):
            prompt, answer = (child, prompt_col), (child, answer_col)
            if not cells.get(prompt):
                raise SheetsError(f"找不到題目內容（{cell_name(*prompt)}）。", 400)
            if not grid.editable(*answer):
                raise SheetsError(f"答案格 {cell_name(*answer)} 無法編輯。", 403)
            original = cells.get(answer)
            text = original.get("stringValue") if original else None
            suffix = child - row + 1
            if original and (end == row + 1 or text not in {f"（{suffix}）", f"({suffix})"}):
                raise SheetsError(f"答案格 {cell_name(*answer)} 已有內容，請使用未作答的學習單。", 400)
            anchors = [[label, label_value], [prompt, cells[prompt]]]
            if text:
                target = adjacent_answer_cell(grid, header, answer)
                if target != answer:
                    anchors.append([answer, original])
                    answer, text = target, None
                    if cells.get(answer):
                        raise SheetsError(f"答案格 {cell_name(*answer)} 已有內容，請使用未作答的學習單。", 400)
                    if not grid.editable(*answer):
                        raise SheetsError(f"答案格 {cell_name(*answer)} 無法編輯。", 403)
            display = f"Q{number}.{suffix}" if end > row + 1 else f"Q{number}"
            source = json.dumps({
                "anchors": anchors,
                "original": text,
            }, ensure_ascii=False)
            result.append((display, *label, *answer, text or "", source))
    if not result:
        raise SheetsError("「題號／題目／作答」表頭下找不到可匯入的題目。", 400)
    return result


def plan_export(db, activity):
    candidates = db.execute(
        """SELECT questions.*, exports.written FROM questions
           LEFT JOIN exports ON exports.question = questions.id
           WHERE activity = ? ORDER BY length(number), number""", (activity,),
    )
    changes = []
    for row in candidates:
        status, winner = outcome(ranking_for(db, row["id"]))
        if not winner and row["written"] is None:
            continue
        source = json.loads(row["source"]) if row["source"] else None
        original = source["original"] if source else row["marker"]
        subquestion_label = original if source else None
        desired = original
        if winner:
            # Native subquestions share the answer cell with their printed label.
            desired = (subquestion_label or "") + winner["answer"]
        changes.append({
            "question": row["id"], "number": row["number"],
            "label": [row["label_row"], row["label_col"]],
            "anchors": source["anchors"] if source else None,
            "cell": [row["answer_row"], row["answer_col"]],
            "expected": row["written"] if row["written"] is not None else original,
            "desired": desired,
            "subquestion_label": subquestion_label,
            "restore": winner is None,
        })
    return changes


def cell_matches(grid, position, expected):
    return grid.cells.get(tuple(position)) == (None if expected is None else {"stringValue": expected})


def anchors_match(grid, change):
    if anchors := change.get("anchors"):
        return all(grid.cells.get(tuple(point)) == expected for point, expected in anchors)
    return cell_matches(grid, change["label"], change["number"])


def verify_targets(grid, changes):
    conflicts = []
    for change in changes:
        number = change["number"]
        label = change["label"]
        point = change["cell"]
        if not anchors_match(grid, change):
            conflicts.append(f"{number}（題號格 {cell_name(*label)}）的題號或題目已變更")
        if not grid.editable(*point):
            conflicts.append(f"{number} 答案格 {cell_name(*point)} 已變更或無法編輯")
            continue
        if cell_matches(grid, point, change["expected"]):
            continue
        current = grid.cells.get(tuple(point), {}).get("stringValue")
        label_text = change["subquestion_label"]
        if label_text and current is not None and current.strip() == label_text:
            change["expected"] = current
        else:
            conflicts.append(f"{number} 答案格 {cell_name(*point)} 已變更或無法編輯")
    if conflicts:
        raise SheetsError("已停止整批回填：" + "；".join(conflicts) + "。", 409)


def migrate_split_answers(grid, changes):
    if not any(change["subquestion_label"] and not change["restore"] for change in changes):
        return
    header, _, _, answer_col = native_columns(grid.cells)
    for change in list(changes):
        marker = change["subquestion_label"]
        if not marker or change["restore"] or change["cell"][1] != answer_col:
            continue
        old = tuple(change["cell"])
        new = adjacent_answer_cell(grid, header, old)
        if old == new:
            continue
        changes.append({**change, "desired": marker, "label_only": True})
        source = {"anchors": [*change["anchors"], [old, {"stringValue": marker}]], "original": None}
        change.update(cell=new, expected=None, desired=change["desired"][len(marker):],
                      subquestion_label=None, new_source=source)


def finish_batch(store, activity, revision, changes):
    with store.transaction() as db:
        for change in changes:
            if change.get("label_only"):
                continue
            if source := change.get("new_source"):
                db.execute(
                    "UPDATE questions SET answer_col = ?, marker = '', source = ? WHERE id = ?",
                    (change["cell"][1], json.dumps(source, ensure_ascii=False), change["question"]),
                )
            if change["restore"]:
                db.execute("DELETE FROM exports WHERE question = ?", (change["question"],))
            else:
                db.execute(
                    """INSERT INTO exports(question,written,revision) VALUES (?,?,?)
                       ON CONFLICT(question) DO UPDATE SET written=excluded.written,revision=excluded.revision""",
                    (change["question"], change["desired"], revision),
                )
        db.execute("DELETE FROM export_batches WHERE activity = ?", (activity,))


def discard_batch(store, activity):
    with store.transaction() as db:
        db.execute("DELETE FROM export_batches WHERE activity = ?", (activity,))


def reconcile_batch(store, sheets, batch, changes, *, keep_pending=False):
    try:
        grid = sheets.read(batch["spreadsheet"], batch["sheet"])
    except SheetsError:
        raise SheetsError("無法核對上次回填結果，請檢查原表權限或連線後再試。") from None
    if all(
        anchors_match(grid, change)
        and cell_matches(grid, change["cell"], change["desired"]) for change in changes
    ):
        finish_batch(store, batch["activity"], batch["revision"], changes)
        return len(changes)
    if all(
        anchors_match(grid, change)
        and cell_matches(grid, change["cell"], change["expected"]) for change in changes
    ):
        if not keep_pending:
            discard_batch(store, batch["activity"])
        return None
    positions = "、".join(f"{change['number']} {cell_name(*change['cell'])}" for change in changes)
    raise SheetsError(f"上次回填結果與預期不符。請先確認這些題目的原格：{positions}。", 409)


def prepare_export(store, sheets, activity):
    activity_id = activity["id"]
    spreadsheet, sheet = activity["spreadsheet"], activity["sheet"]
    with store.read() as db:
        batch = db.execute("SELECT * FROM export_batches WHERE spreadsheet = ?", (spreadsheet,)).fetchone()
    if batch:
        if batch["activity"] != activity_id:
            raise SheetsError("同一試算表有另一場活動的回填待核對，請先處理該場活動。", 409)
        reconcile_batch(store, sheets, batch, json.loads(batch["changes"]))
    with store.read() as db:
        changes = plan_export(db, activity_id)
    if not changes:
        return []
    grid = sheets.read(spreadsheet, sheet)
    migrate_split_answers(grid, changes)
    if len({tuple(change["cell"]) for change in changes}) != len(changes):
        raise SheetsError("回填格位重複，請檢查原工作表。", 409)
    verify_targets(grid, changes)
    return changes


def export_notes(store, sheets, activity, *, expected_digest):
    changes = prepare_export(store, sheets, activity)
    if digest(changes) != expected_digest:
        raise SheetsError("回填內容已變更，請重新預覽後確認。", 409)
    if not changes:
        return 0
    activity_id = activity["id"]
    spreadsheet, sheet = activity["spreadsheet"], activity["sheet"]
    writes = [change for change in changes if change["expected"] != change["desired"]]
    revision = activity["revision"]
    if not writes:
        finish_batch(store, activity_id, revision, changes)
        return 0
    with store.transaction() as db:
        db.execute(
            "INSERT INTO export_batches VALUES (?, ?, ?, ?, ?)",
            (activity_id, spreadsheet, sheet, revision, json.dumps(writes, ensure_ascii=False)),
        )
    try:
        sheets.write(spreadsheet, sheet, [(*change["cell"], change["desired"]) for change in writes])
    except SheetsError as error:
        if not error.uncertain:
            discard_batch(store, activity_id)
            raise
        confirmed = reconcile_batch(store, sheets, {
            "activity": activity_id, "spreadsheet": spreadsheet, "sheet": sheet, "revision": revision,
        }, writes, keep_pending=True)
        if confirmed is None:
            raise SheetsError("Google 回填結果待核對，請稍後再次匯出以重新檢查。") from None
        # Reconcile also records the intended state for unchanged target cells.
        finish_batch(store, activity_id, revision, changes)
        return confirmed
    finish_batch(store, activity_id, revision, changes)
    return len(writes)
