import pytest

from rfab_proxy.config import Settings


def test_defaults_when_environment_is_empty():
    settings = Settings.from_env({})

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.log_level == "INFO"


def test_reads_values_from_environment():
    settings = Settings.from_env(
        {"RFAB_HOST": "0.0.0.0", "RFAB_PORT": "9000", "RFAB_LOG_LEVEL": "debug"}
    )

    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize("port", ["abc", "0", "65536"])
def test_rejects_an_invalid_port(port):
    with pytest.raises(ValueError, match="RFAB_PORT"):
        Settings.from_env({"RFAB_PORT": port})


def test_rejects_an_unknown_log_level():
    with pytest.raises(ValueError, match="RFAB_LOG_LEVEL"):
        Settings.from_env({"RFAB_LOG_LEVEL": "LOUD"})


def test_settings_are_immutable():
    settings = Settings.from_env({})

    with pytest.raises(AttributeError):
        settings.port = 1
