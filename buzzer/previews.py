"""Short-lived, content-bound confirmations; credentials never enter tokens."""
import hashlib
import json

from flask import current_app, session
from itsdangerous import BadData, URLSafeTimedSerializer

from .sheets import SheetsError


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def signer(kind):
    return URLSafeTimedSerializer(current_app.secret_key, salt='buzzer-preview-' + kind)


def sign(kind, data):
    return signer(kind).dumps({**data, 'browser': digest(session['csrf'])})


def verify(kind, token):
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise SheetsError('請先預覽內容，再按確認。', 400)
    try:
        data = signer(kind).loads(token, max_age=1200)
        if not isinstance(data, dict) or data.get('browser') != digest(session['csrf']):
            raise BadData('session changed')
    except BadData:
        raise SheetsError('預覽已過期或驗證失敗，請重新預覽後確認。', 409) from None
    return data
