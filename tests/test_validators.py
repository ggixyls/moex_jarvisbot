from bot.utils.validators import validate_domain, validate_hostname, validate_ip


def test_validate_ip() -> None:
    assert validate_ip("192.168.1.10")
    assert not validate_ip("999.1.1.1")


def test_validate_hostname() -> None:
    assert validate_hostname("ws-01")
    assert not validate_hostname("")


def test_validate_domain() -> None:
    assert validate_domain("corp.local")
    assert not validate_domain("localhost")
