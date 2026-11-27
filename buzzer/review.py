def lock_rankings(db, activity):
    db.execute(
        """INSERT INTO rankings(question, team, rank)
           SELECT question, team, ROW_NUMBER() OVER (PARTITION BY question ORDER BY sequence)
           FROM submissions JOIN questions ON questions.id = submissions.question
           WHERE activity = ?""",
        (activity,),
    )


def ranking_for(db, question):
    return db.execute(
        """SELECT rankings.team AS 'group', groups.name, rankings.rank,
                  submissions.answer, submissions.timestamp
           FROM rankings JOIN submissions USING (question, team) JOIN groups ON groups.id = rankings.team
           WHERE rankings.question = ? ORDER BY rankings.rank""",
        (question,),
    ).fetchall()


def outcome(ranking):
    if not ranking:
        return "empty", None
    return "winner", {key: ranking[0][key] for key in ("group", "name", "answer")}
