from contextlib import contextmanager
from pathlib import Path
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'ready',
    spreadsheet TEXT, sheet INTEGER, revision INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open ON activities(phase) WHERE phase = 'open';
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY, activity INTEGER NOT NULL REFERENCES activities(id),
    name TEXT NOT NULL, UNIQUE(activity, name)
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY, activity INTEGER NOT NULL REFERENCES activities(id),
    number TEXT NOT NULL, label_row INTEGER NOT NULL, label_col INTEGER NOT NULL,
    answer_row INTEGER NOT NULL, answer_col INTEGER NOT NULL, marker TEXT NOT NULL, source TEXT,
    UNIQUE(activity, number), UNIQUE(activity, answer_row, answer_col)
);
CREATE TABLE IF NOT EXISTS memberships (
    browser TEXT NOT NULL, activity INTEGER NOT NULL REFERENCES activities(id),
    team INTEGER NOT NULL REFERENCES groups(id),
    PRIMARY KEY(browser, activity)
);
CREATE TABLE IF NOT EXISTS transfer_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity INTEGER NOT NULL REFERENCES activities(id), browser TEXT NOT NULL,
    source INTEGER NOT NULL REFERENCES groups(id), target INTEGER NOT NULL REFERENCES groups(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected'))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_transfer
ON transfer_requests(activity, browser) WHERE status = 'pending';
CREATE TABLE IF NOT EXISTS submissions (
    question INTEGER NOT NULL REFERENCES questions(id), team INTEGER NOT NULL REFERENCES groups(id),
    answer TEXT NOT NULL, timestamp INTEGER NOT NULL, sequence INTEGER NOT NULL UNIQUE,
    PRIMARY KEY(question, team)
);
CREATE TABLE IF NOT EXISTS receipts (
    activity INTEGER NOT NULL REFERENCES activities(id), browser TEXT NOT NULL, receipt TEXT NOT NULL,
    number TEXT NOT NULL, answer TEXT NOT NULL, response TEXT NOT NULL,
    PRIMARY KEY(activity, browser, receipt)
);
CREATE TABLE IF NOT EXISTS rankings (
    question INTEGER NOT NULL, team INTEGER NOT NULL, rank INTEGER NOT NULL,
    correct INTEGER CHECK(correct IN (0, 1)),
    PRIMARY KEY(question, team), UNIQUE(question, rank),
    FOREIGN KEY(question, team) REFERENCES submissions(question, team)
);
CREATE TABLE IF NOT EXISTS exports (
    question INTEGER PRIMARY KEY REFERENCES questions(id), written TEXT NOT NULL,
    revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS export_batches (
    activity INTEGER PRIMARY KEY REFERENCES activities(id), spreadsheet TEXT NOT NULL UNIQUE,
    sheet INTEGER NOT NULL, revision INTEGER NOT NULL, changes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS round_history (
    id INTEGER PRIMARY KEY, activity INTEGER NOT NULL REFERENCES activities(id),
    snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identifiers (
    kind TEXT PRIMARY KEY, last_id INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.read() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(SCHEMA)
            for table in ("activities", "groups"):
                db.execute(
                    f"INSERT OR IGNORE INTO identifiers SELECT ?, COALESCE(MAX(id), 0) FROM {table}",
                    (table,),
                )
            if "source" not in {row["name"] for row in db.execute("PRAGMA table_info(questions)")}:
                db.execute("ALTER TABLE questions ADD COLUMN source TEXT")
            if "worksheet_version" not in {row["name"] for row in db.execute("PRAGMA table_info(activities)")}:
                db.execute("ALTER TABLE activities ADD COLUMN worksheet_version INTEGER NOT NULL DEFAULT 0")
            if "version" not in {row["name"] for row in db.execute("PRAGMA table_info(memberships)")}:
                db.execute("ALTER TABLE memberships ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
            if "import_key" not in {row["name"] for row in db.execute("PRAGMA table_info(activities)")}:
                db.execute("ALTER TABLE activities ADD COLUMN import_key TEXT")
            if "joined_once" not in {row["name"] for row in db.execute("PRAGMA table_info(activities)")}:
                db.execute("ALTER TABLE activities ADD COLUMN joined_once INTEGER NOT NULL DEFAULT 0")
                db.execute("""UPDATE activities SET joined_once = 1 WHERE
                    EXISTS (SELECT 1 FROM memberships WHERE activity = activities.id) OR
                    EXISTS (SELECT 1 FROM receipts WHERE activity = activities.id) OR
                    EXISTS (SELECT 1 FROM transfer_requests WHERE activity = activities.id) OR
                    EXISTS (SELECT 1 FROM submissions JOIN questions ON questions.id = submissions.question
                            WHERE questions.activity = activities.id)""")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS activity_import_key ON activities(import_key) WHERE import_key IS NOT NULL")
            db.execute("INSERT OR IGNORE INTO identifiers SELECT 'submissions', COALESCE(MAX(sequence), 0) FROM submissions")
            db.commit()

    @contextmanager
    def read(self):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.read() as db, db:
            db.execute("BEGIN IMMEDIATE")
            yield db
