from __future__ import annotations

import json

import pytest

from skinforge import updater


def test_version_tuple_handles_v_prefix_and_suffix() -> None:
    assert updater._version_tuple("v1.2.3") == (1, 2, 3)
    assert updater._version_tuple("1.2.3-rc.1") == (1, 2, 3)


def test_version_tuple_rejects_invalid_version() -> None:
    with pytest.raises(updater.UpdateError):
        updater._version_tuple("not-a-version")


def test_check_for_update_detects_newer_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater, "_github_token", lambda: "")
    monkeypatch.setattr(
        updater,
        "_request",
        lambda *_args, **_kwargs: json.dumps(
            {
                "tag_name": "v999.0.0",
                "html_url": "https://github.com/M0rphy2020/LEAGUE-SKINFORGE-AI/releases/tag/v999.0.0",
                "draft": False,
                "prerelease": False,
                "assets": [
                    {
                        "name": "skinforge_ai-999.0.0-py3-none-any.whl",
                        "browser_download_url": (
                            "https://github.com/M0rphy2020/LEAGUE-SKINFORGE-AI/releases/download/"
                            "v999.0.0/skinforge_ai-999.0.0-py3-none-any.whl"
                        ),
                    }
                ],
            }
        ).encode(),
    )
    result = updater.check_for_update()
    assert result["update_available"] is True
    assert result["latest_version"] == "999.0.0"
    assert result["wheel"]["name"].endswith(".whl")


def test_install_requires_a_release_wheel() -> None:
    with pytest.raises(updater.UpdateError, match="no SkinForge wheel"):
        updater.install_latest_update(
            {"update_available": True, "latest_version": "999.0.0", "wheel": None}
        )
