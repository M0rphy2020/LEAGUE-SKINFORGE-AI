from pathlib import Path

from skinforge.bininspect import inspect_bin


def test_json_candidate_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "sample.bin"
    source.write_text('{"key": 1}', encoding="utf-8")
    report = inspect_bin(source)
    assert report["utf8_text_candidate"] is True
    assert report["json_candidate"] is True


def test_binary_candidate_is_not_claimed_as_decoded(tmp_path: Path) -> None:
    source = tmp_path / "opaque.bin"
    source.write_bytes(bytes([0, 255, 3, 0, 128]))
    report = inspect_bin(source)
    assert report["json_candidate"] is False


def test_binary_inspection_reports_readable_strings_and_hex(tmp_path: Path) -> None:
    source = tmp_path / "strings.bin"
    source.write_bytes(b"\\x00\\x01ChampionSkinName\\x00\\xff")
    report = inspect_bin(source)
    assert report["readable_strings"][0]["text"] == "ChampionSkinName"
    assert report["readable_strings"][0]["offset"] == 2
    assert "hex_preview" in report
