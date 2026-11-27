import hmac
import secrets

from flask import session


def matches(left, right):
    return hmac.compare_digest(left.encode(), right.encode())


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe()
    return session["csrf"]
