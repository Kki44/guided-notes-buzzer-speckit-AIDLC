import os


def settings():
    values = {}
    for name in ("TEACHER_PASSWORD", "SECRET_KEY"):
        value = os.environ.get(f"BUZZER_{name}")
        if not value or not value.strip():
            raise RuntimeError(f"請設定環境變數 BUZZER_{name}")
        values[name] = value
    return values
