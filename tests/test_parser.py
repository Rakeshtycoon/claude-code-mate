from pathlib import Path

import pytest

from stn_reader.parser import StnParseError, parse_stn_file


def test_parse_reads_file_metadata(tmp_path: Path) -> None:
    stn = tmp_path / "sample.stn"
    payload = b"STN\x00" + b"\x01" * 32
    stn.write_bytes(payload)

    model = parse_stn_file(stn)

    assert model.source_path == stn
    assert model.byte_size == len(payload)
    assert model.header == payload[:16]


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(StnParseError):
        parse_stn_file(tmp_path / "does-not-exist.stn")
