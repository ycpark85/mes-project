# app/core/auth.py

class DummyUser:
    def __init__(self):
        self.username = "admin"


def get_current_user():
    # 인증 시스템이 없으므로 임시로 admin을 반환
    return DummyUser()