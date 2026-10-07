from rfab_proxy import __main__ as entrypoint


def test_main_serves_the_instrumented_app_factory_with_uvicorn(monkeypatch):
    calls = []
    monkeypatch.setattr(
        entrypoint.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    monkeypatch.setenv("RFAB_HOST", "0.0.0.0")
    monkeypatch.setenv("RFAB_PORT", "9000")

    entrypoint.main()

    (args, kwargs), = calls
    assert args == ("rfab_proxy.app:create_asgi_app",)
    assert kwargs["factory"] is True
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 9000
    assert kwargs["log_config"] is None
