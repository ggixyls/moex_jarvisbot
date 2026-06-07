_SENSITIVE_KEYS = frozenset({"password", "token", "admin_pass"})


def mask_sensitive_data(data: object) -> object:
    if isinstance(data, dict):
        return {
            key: "***" if key in _SENSITIVE_KEYS else mask_sensitive_data(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data
