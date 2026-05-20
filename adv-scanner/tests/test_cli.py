"""End-to-end tests for the adv-analyzer CLI."""
import json

from advkit.tools.cli import main


def test_inspect(synthetic_adv_path, capsys):
    rc = main(["inspect", synthetic_adv_path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "X-ray slices" in out
    assert "SECTIONS" in out


def test_report_emits_json(synthetic_adv_path, capsys):
    rc = main(["report", synthetic_adv_path])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert parsed["slice_count"] == 4
    assert "section_entropy" in parsed


def test_hexdump(synthetic_adv_path, capsys):
    rc = main(["hexdump", synthetic_adv_path, "--length", "32"])
    assert rc == 0
    assert "00000000" in capsys.readouterr().out


def test_entropy(synthetic_adv_path, capsys):
    rc = main(["entropy", synthetic_adv_path, "--window", "65536"])
    assert rc == 0
    assert "entropy profile" in capsys.readouterr().out


def test_volume_export(synthetic_adv_path, tmp_path, capsys):
    out = tmp_path / "v.npy"
    rc = main(["-q", "volume", synthetic_adv_path,
               "--downsample", "8", "-o", str(out)])
    assert rc == 0
    assert out.is_file()


def test_inclusions(synthetic_adv_path, tmp_path, capsys):
    report = tmp_path / "inc.json"
    rc = main(["-q", "inclusions", synthetic_adv_path,
               "--downsample", "4", "--json", str(report)])
    assert rc == 0
    assert json.loads(report.read_text())["count"] >= 0


def test_missing_file_exits():
    try:
        main(["inspect", "/nonexistent/path.adv"])
    except SystemExit as exc:
        assert exc.code != 0
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")
