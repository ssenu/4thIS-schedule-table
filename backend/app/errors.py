"""라우터가 던지고 main.py의 핸들러가 HTTP 응답으로 바꾸는 예외."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Unauthorized(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class TooManyAttempts(DomainError):
    status_code = 429

    def __init__(self, detail: str, retry_after: int):
        super().__init__(detail)
        self.retry_after = retry_after
