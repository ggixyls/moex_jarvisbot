from bot.utils.masking import mask_sensitive_data


def test_mask_sensitive_data() -> None:
    data = {
        "username": "admin",
        "admin_pass": "secret",
        "token": "abc",
        "nested": {"password": "123"},
    }
    masked = mask_sensitive_data(data)
    assert masked["admin_pass"] == "***"
    assert masked["token"] == "***"
    assert masked["nested"]["password"] == "***"
    assert masked["username"] == "admin"
