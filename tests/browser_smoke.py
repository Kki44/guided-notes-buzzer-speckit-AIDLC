"""Explicit Playwright acceptance: pytest -q tests/browser_smoke.py."""
import os
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from test_import_join import FakeSheets, URL, prepared
from test_native_notes import native_cells
from conftest import send


@pytest.fixture
def live(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(5)


def login(page, root, suffix="/teacher"):
    page.goto(root + suffix)
    page.get_by_label("管理密碼").fill(os.environ["BUZZER_TEACHER_PASSWORD"])
    page.get_by_role("button", name="登入", exact=True).click()
    expect(page.locator("#notes")).to_be_visible()


def read_activity(page, root, activity, group="A"):
    page.goto(root)
    page.get_by_label("活動識別碼").fill(str(activity))
    page.get_by_role("button", name="讀取活動", exact=True).click()
    expect(page.locator("#join")).to_be_visible()
    page.get_by_label("組別", exact=True).select_option(label=group)
    page.get_by_role("button", name="加入", exact=True).click()
    expect(page.locator("#membership")).to_have_text("已加入 " + group)


def write_answer(page, question, value):
    card = page.locator("#questions > section").filter(has=page.get_by_role("heading", name=question, exact=True))
    card.get_by_role("button", name="修改答案 " + question if card.locator(".submitted-preview").count() else "開始作答 " + question, exact=True).click()
    page.get_by_label("答案", exact=True).fill(value)
    page.get_by_role("button", name="送出答案", exact=True).click()
    return card


def test_classroom_browser_flow(app, live):
    fake = FakeSheets()
    fake.cells = native_cells([(4, 1, "處理器簡稱", None), (6, 2, "二進位", None)])
    fake.writes = []
    def write(_, __, changes):
        fake.writes.append(changes)
        for row, col, value in changes:
            fake.cells[row, col] = {"stringValue": value}
    fake.write = write
    app.extensions["sheets"] = fake
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        try:
            teacher = browser.new_context().new_page()
            teacher.set_default_timeout(8000)
            errors = []
            teacher.on("pageerror", lambda error: errors.append(str(error)))
            accept_dialog = lambda dialog: dialog.accept()
            teacher.on("dialog", accept_dialog)
            login(teacher, live)
            teacher.get_by_label("活動名稱").fill("Browser class")
            teacher.get_by_label("Google Sheets 連結").fill(URL)
            teacher.get_by_role("button", name="讀取工作表", exact=True).click()
            expect(teacher.get_by_label("工作表", exact=True)).to_have_value("0")
            def change_input_before_preview_response(route):
                response = route.fetch()
                teacher.get_by_label("活動名稱").fill("Changed while loading")
                route.fulfill(response=response)
            teacher.route("**/api/guided-notes/preview", change_input_before_preview_response)
            teacher.get_by_role("button", name="預覽題目", exact=True).click()
            expect(teacher.locator("#feedback")).to_have_text("匯入資料已變更，請重新預覽。")
            expect(teacher.locator("#import-preview")).to_be_hidden()
            teacher.unroute("**/api/guided-notes/preview")
            teacher.get_by_label("活動名稱").fill("Browser class")
            teacher.get_by_role("button", name="預覽題目", exact=True).click()
            expect(teacher.locator("#import-preview")).to_contain_text("G5")
            teacher.get_by_role("button", name="取消匯入", exact=True).click()
            expect(teacher.locator("#activities option")).to_have_count(1)
            teacher.get_by_role("button", name="預覽題目", exact=True).click()
            teacher.get_by_role("button", name="確認匯入並建立活動", exact=True).click()
            expect(teacher.locator("#feedback")).to_contain_text("已確認匯入並建立活動")
            activity = teacher.locator("#activities").input_value()
            assert teacher.url == live + "/teacher/activities/" + activity
            expect(teacher.locator("#activity-url")).to_have_value(teacher.url)
            teacher.get_by_role("button", name="批次建立組別", exact=True).click()
            expect(teacher.locator("#group-codes li")).to_have_count(2)
            teacher.get_by_label("組別名稱", exact=True).fill("Extra")
            teacher.get_by_role("button", name="建立組別", exact=True).click()
            expect(teacher.locator("#group-codes li")).to_have_count(3)
            teacher.get_by_role("button", name="刪除組別 Extra", exact=True).click()
            expect(teacher.locator("#group-codes li")).to_have_count(2)
            student_a, student_b = browser.new_page(), browser.new_page()
            for page in (student_a, student_b):
                page.on("pageerror", lambda error: errors.append(str(error)))
            read_activity(student_a, live, activity, "第 1 組")
            read_activity(student_b, live, activity, "第 2 組")
            teammate = teacher.context.new_page()
            read_activity(teammate, live, activity, "第 1 組")
            teacher.get_by_role("button", name="開放全部題目", exact=True).click()
            expect(student_a.locator("#phase")).to_have_text("搶答開放")
            card = write_answer(student_a, "Q1", "A first")
            expect(card.locator(".question-status")).to_have_text("已作答")
            expect(teammate.locator(".submitted-preview")).to_have_text("上一次作答：A first")
            write_answer(student_b, "Q1", "B private")
            write_answer(student_a, "Q1", "A first")
            expect(student_a.locator("#feedback")).to_have_text("答案未變更，無須重新提交")
            write_answer(student_a, "Q1", "A revised")
            expect(card.locator(".submitted-preview")).to_have_text("上一次作答：A revised")
            student_a.get_by_role("button", name="開始作答 Q2", exact=True).click()
            expect(card.locator(".submitted-preview")).to_be_visible()
            student_a.set_viewport_size({"width": 390, "height": 844})
            assert student_a.evaluate("document.documentElement.scrollWidth === innerWidth")
            assert card.bounding_box()["height"] < student_a.locator("#questions > section").filter(has_text="二進位").bounding_box()["height"]
            expect(teacher.locator(".submission-time")).to_have_count(2)
            teacher.get_by_role("button", name="結束搶答", exact=True).click()
            expect(student_a.locator("#phase")).to_have_text("搶答結束")
            expect(student_a.locator(".own-rank").first).to_have_text("本組第 2 名")
            expect(student_a.locator(".review-result").first).to_have_text("搶答成功組別：第 2 組")
            assert "B private" not in student_a.locator("body").inner_text()
            expect(teacher.get_by_role("button", name="開放全部題目", exact=True)).to_be_disabled()
            teacher.get_by_role("button", name="預覽回填 Google Sheets", exact=True).click()
            expect(teacher.locator("#export-preview-content")).to_contain_text("B private")
            assert fake.writes == []
            teacher.get_by_role("button", name="取消回填", exact=True).click()
            assert fake.writes == []
            teacher.get_by_role("button", name="預覽回填 Google Sheets", exact=True).click()
            teacher.get_by_role("button", name="確認寫回 Google Sheets", exact=True).click()
            expect(teacher.locator("#feedback")).to_have_text("已回填 1 格。")
            assert fake.cells[4, 6] == {"stringValue": "B private"}
            saved_url = teacher.url
            teacher.reload()
            expect(teacher.locator("#phase")).to_have_text("搶答結束")
            teacher.locator("#activities").select_option("")
            expect(teacher.get_by_label("Google Sheets 連結")).to_be_enabled()
            fake.cells = native_cells([(4, 1, "新的學習單題目", None)])
            teacher.get_by_label("活動名稱").fill("Next class")
            teacher.get_by_label("Google Sheets 連結").fill(URL)
            teacher.get_by_role("button", name="預覽題目", exact=True).click()
            teacher.get_by_role("button", name="確認匯入並建立活動", exact=True).click()
            expect(teacher.locator("#questions")).to_contain_text("新的學習單題目")
            assert teacher.url != saved_url
            teacher.goto(saved_url)
            expect(teacher.locator("#questions")).to_contain_text("處理器簡稱")
            assert teacher.locator("#reopen-options, #transfer-requests, #round-history, .submission-progress").count() == 0
            Path("instance").mkdir(exist_ok=True)
            teacher.screenshot(path="instance/core-alignment-teacher.png", full_page=True)
            student_a.screenshot(path="instance/core-alignment-student.png", full_page=True)
            teacher.remove_listener("dialog", accept_dialog)
            teacher.once("dialog", lambda dialog: dialog.dismiss())
            teacher.get_by_role("button", name="刪除活動", exact=True).click()
            expect(teacher.locator("#phase")).to_have_text("搶答結束")
            teacher.once("dialog", lambda dialog: dialog.accept())
            teacher.get_by_role("button", name="刪除活動", exact=True).click()
            expect(teacher.locator("#feedback")).to_have_text("已刪除活動；Google Sheets 內容保留。")
            expect(teacher.locator("#activities")).to_have_value("")
            assert fake.writes
            assert errors == []
        finally:
            browser.close()


def test_direct_reselection_clears_shared_tab_drafts_but_preserves_old_group(app, teacher, prepared, live):
    _, path, a, b = prepared
    activity = path.rsplit("/", 1)[1]
    send(teacher, path + "/open")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        try:
            context = browser.new_context()
            first, shared = context.new_page(), context.new_page()
            teammate = browser.new_page()
            read_activity(first, live, activity)
            read_activity(teammate, live, activity)
            write_answer(first, "Q1", "original A")
            shared.goto(live)
            expect(shared.locator(".submitted-preview")).to_have_text("上一次作答：original A")
            shared.get_by_role("button", name="修改答案 Q1", exact=True).click()
            shared.get_by_label("答案", exact=True).fill("stale A draft")
            # Hold the old tab's snapshot, switch from a second tab, then submit the old version.
            shared.route("**/view?audience=student", lambda route: route.abort())
            first.get_by_label("組別", exact=True).select_option(label="B")
            first.get_by_role("button", name="重新選組", exact=True).click()
            expect(first.locator("#membership")).to_have_text("已加入 B")
            shared.get_by_role("button", name="送出答案", exact=True).click()
            expect(shared.locator("#feedback")).to_contain_text("組別已變更")
            shared.unroute("**/view?audience=student")
            expect(shared.locator("#membership")).to_have_text("已加入 B")
            expect(shared.locator("#answer")).to_be_hidden()
            expect(teammate.locator(".submitted-preview")).to_have_text("上一次作答：original A")
            write_answer(first, "Q1", "new B")
            expect(shared.locator(".submitted-preview")).to_have_text("上一次作答：new B")
            expect(teammate.locator(".submitted-preview")).to_have_text("上一次作答：original A")
            first.get_by_label("組別", exact=True).select_option(label="A")
            first.get_by_role("button", name="重新選組", exact=True).click()
            expect(first.locator("#membership")).to_have_text("已加入 A")
            expect(first.locator(".submitted-preview")).to_have_text("上一次作答：original A")
            first.set_viewport_size({"width": 390, "height": 844})
            assert first.evaluate("document.documentElement.scrollWidth === innerWidth")
            assert first.locator("#transfer, input[name=code]").count() == 0
        finally:
            browser.close()
