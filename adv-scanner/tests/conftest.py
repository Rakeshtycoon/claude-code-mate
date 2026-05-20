"""Shared test fixtures.

The real 45 MB sample is not committed. Instead a *synthetic* .adv file is
built that reproduces the reverse-engineered layout (header GUIDs, version,
size fields, FILETIME, calibration, length-prefixed strings, a run of
grayscale slice JPEGs and a run of RGB thumbnail JPEGs). Tests run fully
offline against it.

Set the ``ADV_SAMPLE`` environment variable to a real .adv path to also
exercise the suite against genuine data.
"""
from __future__ import annotations

import io
import os
import struct

import numpy as np
import pytest
from PIL import Image

SLICE_W, SLICE_H = 1024, 1280
THUMB_W, THUMB_H = 98, 98
N_SLICES = 4
N_THUMBS = 3


def _jpeg(image: Image.Image, quality: int = 60) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _gradient_slice(seed: int) -> bytes:
    """A 1024x1280 grayscale JPEG with a smooth gradient + a dark blob."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:SLICE_H, 0:SLICE_W]
    img = (80 + 120 * (xx / SLICE_W)).astype(np.float64)
    img += rng.normal(0, 4, img.shape)
    # a dark circular "inclusion" so detection tests have something to find
    cy, cx, r = SLICE_H // 2, SLICE_W // 2, 60
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 < r * r
    img[mask] = 10
    return _jpeg(Image.fromarray(img.clip(0, 255).astype(np.uint8), "L"))


def _thumb(seed: int) -> bytes:
    rng = np.random.default_rng(seed + 1000)
    arr = rng.integers(0, 256, (THUMB_H, THUMB_W, 3), dtype=np.uint8)
    return _jpeg(Image.fromarray(arr, "RGB"))


def build_synthetic_adv() -> bytes:
    """Construct a byte-accurate miniature .adv container."""
    header = bytearray(512)
    header[0:16] = bytes(range(16))                       # class GUID
    struct.pack_into("<I", header, 16, 2)                 # version
    header[32:48] = bytes(range(16, 32))                  # secondary GUID
    # FILETIME for 2024-01-01T00:00:00Z
    filetime = int((1704067200 + 11644473600) * 1e7)
    struct.pack_into("<Q", header, 60, filetime)
    struct.pack_into("<d", header, 68, 1.842)             # calibration
    for off in range(76, 124, 8):                         # AABB sentinels
        struct.pack_into("<d", header, off, -1.0)
    # length-prefixed metadata strings
    cursor = 200
    for s in (b"168001688475", b"Fast"):
        struct.pack_into("<I", header, cursor, len(s))
        header[cursor + 4:cursor + 4 + len(s)] = s
        cursor += 4 + len(s)

    body = bytearray(header)
    body += b"\x00" * 4096                                # raw body block
    for i in range(N_SLICES):
        body += _gradient_slice(i)
    body += b"\xab" * 2048                                # intermediate block
    for i in range(N_THUMBS):
        body += _thumb(i)
    body += b"\x00" * 64                                  # trailer

    struct.pack_into("<I", body, 20, len(body) - 24)
    struct.pack_into("<I", body, 24, len(body) - 76)
    return bytes(body)


@pytest.fixture(scope="session")
def synthetic_adv_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("adv") / "synthetic.adv"
    path.write_bytes(build_synthetic_adv())
    return str(path)


@pytest.fixture(scope="session")
def synthetic_adv_bytes() -> bytes:
    return build_synthetic_adv()


@pytest.fixture(scope="session")
def real_adv_path() -> str:
    path = os.environ.get("ADV_SAMPLE")
    if not path or not os.path.isfile(path):
        pytest.skip("ADV_SAMPLE not set to a real .adv file")
    return path
