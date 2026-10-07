import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "ci_versions.py"


@pytest.fixture
def ci_versions():
    spec = importlib.util.spec_from_file_location("ci_versions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mise_toml(tmp_path):
    path = tmp_path / "mise.toml"
    path.write_text(
        '[tools]\n'
        'python = ["3.14", "3.15"]\n'
        'uv = "0.12.23"\n'
    )
    return path


def test_lists_every_python_version_with_its_tox_env(ci_versions, mise_toml):
    result = ci_versions.versions(mise_toml)

    assert result["python"] == [
        {"python": "3.14", "toxenv": "py314"},
        {"python": "3.15", "toxenv": "py315"},
    ]


def test_reports_the_uv_version(ci_versions, mise_toml):
    assert ci_versions.versions(mise_toml)["uv"] == "0.12.23"


def test_accepts_a_single_python_version(ci_versions, tmp_path):
    path = tmp_path / "mise.toml"
    path.write_text('[tools]\npython = "3.14"\nuv = "0.12.23"\n')

    assert ci_versions.versions(path)["python"] == [{"python": "3.14", "toxenv": "py314"}]


def test_main_prints_valid_json_for_the_repository_mise_toml(ci_versions, capsys):
    ci_versions.main([str(ROOT / "mise.toml")])

    output = json.loads(capsys.readouterr().out)
    assert [entry["python"] for entry in output["python"]] == ["3.14", "3.15"]
    assert output["uv"]


def test_reduces_full_and_prerelease_pins_to_major_minor(ci_versions, tmp_path):
    path = tmp_path / "mise.toml"
    path.write_text('[tools]\npython = ["3.14.8", "3.15.0rc3"]\nuv = "0.12.23"\n')

    assert ci_versions.versions(path)["python"] == [
        {"python": "3.14", "toxenv": "py314"},
        {"python": "3.15", "toxenv": "py315"},
    ]
