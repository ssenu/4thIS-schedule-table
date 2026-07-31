import pytest

from app.auth import AttemptLimiter, LockedOut, hash_password, verify_password


def test_hash_is_not_plaintext():
    hashed = hash_password("1234")
    assert hashed != "1234"
    assert len(hashed) > 20


def test_verify_accepts_correct_password():
    assert verify_password("1234", hash_password("1234")) is True


def test_verify_rejects_wrong_password():
    assert verify_password("9999", hash_password("1234")) is False


def test_same_password_hashes_differently_each_time():
    assert hash_password("1234") != hash_password("1234")


def test_verify_survives_a_malformed_hash():
    assert verify_password("1234", "not-a-bcrypt-hash") is False


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return AttemptLimiter(max_attempts=3, lockout_seconds=600, clock=clock)


def test_fresh_key_is_allowed(limiter):
    limiter.check("1.2.3.4:member:1")


def test_remaining_attempts_count_down(limiter):
    assert limiter.record_failure("k") == 2
    assert limiter.record_failure("k") == 1
    assert limiter.record_failure("k") == 0


def test_lockout_after_max_attempts(limiter):
    for _ in range(3):
        limiter.record_failure("k")
    with pytest.raises(LockedOut):
        limiter.check("k")


def test_lockout_reports_retry_after(limiter):
    for _ in range(3):
        limiter.record_failure("k")
    with pytest.raises(LockedOut) as excinfo:
        limiter.check("k")
    assert excinfo.value.retry_after == 601


def test_lockout_expires(limiter, clock):
    for _ in range(3):
        limiter.record_failure("k")
    clock.advance(601)
    limiter.check("k")


def test_success_clears_failures(limiter):
    limiter.record_failure("k")
    limiter.record_failure("k")
    limiter.record_success("k")
    assert limiter.record_failure("k") == 2


def test_keys_are_tracked_independently(limiter):
    for _ in range(3):
        limiter.record_failure("a")
    limiter.check("b")
