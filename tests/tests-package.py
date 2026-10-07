import rfab_proxy


def test_version_is_exposed():
    assert isinstance(rfab_proxy.__version__, str)
    assert rfab_proxy.__version__


def test_package_is_licensed_agpl_3_0_or_later():
    from importlib.metadata import metadata

    meta = metadata("rfab-proxy")
    assert meta["License-Expression"] == "AGPL-3.0-or-later"
    assert "LICENSE" in meta.get_all("License-File")
