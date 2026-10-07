import rfab_proxy


def test_version_is_exposed():
    assert isinstance(rfab_proxy.__version__, str)
    assert rfab_proxy.__version__
