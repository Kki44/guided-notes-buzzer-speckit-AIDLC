import json


def prior_receipt(db, activity, browser, receipt):
    return db.execute(
        """SELECT number, answer, response FROM receipts
           WHERE activity = ? AND browser = ? AND receipt = ?""",
        (activity, browser, receipt),
    ).fetchone()


def save_submission(db, activity, browser, team, question, number, answer, receipt, received):
    timestamp, sequence = received
    response = {"answer": answer, "timestamp": timestamp, "sequence": sequence}
    db.execute(
        """INSERT INTO submissions(question, team, answer, timestamp, sequence)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(question, team) DO UPDATE SET
               answer=excluded.answer, timestamp=excluded.timestamp, sequence=excluded.sequence""",
        (question, team, answer, timestamp, sequence),
    )
    db.execute(
        """INSERT INTO receipts(activity,browser,receipt,number,answer,response)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (activity, browser, receipt, number, answer, json.dumps(response, ensure_ascii=False)),
    )
    return response


def submissions_for(db, question):
    return db.execute(
        """SELECT team AS 'group', groups.name, answer, timestamp, sequence FROM submissions
           JOIN groups ON groups.id = submissions.team WHERE question = ? ORDER BY sequence""",
        (question,),
    ).fetchall()
