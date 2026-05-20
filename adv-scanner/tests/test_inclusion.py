"""Tests for volumetric inclusion detection."""
import numpy as np

from advkit.inclusion.detector import detect, label_volume, otsu_threshold


def _stone_with_void():
    """A bright cube of 'stone' with one dark enclosed cubic void."""
    vol = np.zeros((40, 40, 40), dtype=np.uint8)
    vol[5:35, 5:35, 5:35] = 200          # stone body
    vol[18:24, 18:24, 18:24] = 0         # enclosed inclusion / void
    return vol


def test_detect_finds_enclosed_void():
    vol = _stone_with_void()
    result = detect(vol, min_voxels=4)
    assert result.count == 1
    inc = result.inclusions[0]
    assert inc.voxel_count == 6 ** 3
    # centroid sits near the void centre (~21, 21, 21)
    cz, cy, cx = inc.centroid
    assert abs(cz - 21) < 2 and abs(cy - 21) < 2 and abs(cx - 21) < 2


def test_detect_ignores_surface_dark_region():
    # A dark notch open to the outside is NOT an enclosed inclusion.
    vol = np.zeros((40, 40, 40), dtype=np.uint8)
    vol[5:35, 5:35, 5:35] = 200
    vol[5:15, 5:35, 5:15] = 0            # carved from the corner -> not enclosed
    result = detect(vol, min_voxels=4)
    assert result.count == 0


def test_otsu_threshold_between_modes():
    # A bimodal {0, 200} volume: Otsu must land below the bright stone peak
    # so that ``volume > threshold`` selects the stone.
    vol = _stone_with_void()
    t = otsu_threshold(vol)
    assert 0 <= t < 200
    assert (vol > t).sum() == (vol == 200).sum()


def test_min_voxels_filters_noise():
    vol = _stone_with_void()
    vol[10, 10, 10] = 0                  # 1-voxel speck
    result = detect(vol, min_voxels=10)
    assert result.count == 1             # speck dropped, real void kept


def test_label_volume_matches_result():
    vol = _stone_with_void()
    result = detect(vol, min_voxels=4)
    labels = label_volume(vol, result)
    assert labels.shape == vol.shape
    assert set(np.unique(labels)) - {0} == {i.label for i in result.inclusions}


def test_result_serialisable():
    import json
    result = detect(_stone_with_void(), min_voxels=4)
    json.dumps(result.as_dict())
    assert result.defect_fraction > 0
