"""Tests for volume reconstruction and structure discovery."""
import numpy as np

from advkit.parsers.adv import AdvFile
from advkit.volume.discover import brute_force_dimensions, profile_block
from advkit.volume.slices import SliceStack


def test_build_volume(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        stack = SliceStack(adv)
        vol = stack.build_volume(downsample=4)
        assert vol.ndim == 3
        assert vol.shape[0] == 1  # 4 slices // downsample 4
        assert vol.dtype == np.uint8


def test_volume_stats_and_normalize(synthetic_adv_path):
    with AdvFile.open(synthetic_adv_path) as adv:
        stack = SliceStack(adv)
        vol = stack.build_volume(downsample=8)
        stats = stack.stats(vol)
        assert stats.voxel_count == vol.size
        assert 0 <= stats.min <= stats.max <= 255
        norm = stack.normalize(vol)
        assert norm.min() == 0
        assert norm.max() == 255


def test_brute_force_dimensions_recovers_width():
    # An image with a clear 200-px stride: each row is a ramp (high internal
    # variance) and adjacent rows differ only by small noise -> the true
    # width gives the strongest adjacent-row correlation.
    rng = np.random.default_rng(1)
    ramp = np.linspace(0, 255, 200)
    rows = np.clip(ramp + rng.normal(0, 6, (64, 200)), 0, 255).astype(np.uint8)
    block = rows.tobytes()
    guesses = brute_force_dimensions(block, min_width=196, max_width=204,
                                     bytes_per_pixel=(1,), sample_rows=64)
    assert guesses[0].width == 200


def test_profile_block_classification():
    assert profile_block(b"\x00" * 10000).verdict.startswith("padding")
    assert "text" in profile_block(b"hello world " * 1000).verdict
