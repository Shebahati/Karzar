"""Detect ShopMill logo watermark (yellow Shop + navy Mill, top-left)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class DetectionResult:
    detected: bool
    bbox: tuple[int, int, int, int] | None
    confidence: str
    yellow_px: int
    dark_px: int
    mode: str
    reason: str = ""


def _load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def _yellow_mask(rgb: np.ndarray, y2: int, x2: int) -> np.ndarray:
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    yellow = (
        (r > 190)
        & (g > 130)
        & (g < 220)
        & (b < 100)
        & ((r - b) > 100)
        & ((g - b) > 50)
    )
    yellow[y2:, :] = False
    yellow[:, x2:] = False
    return yellow


def _yellow_components(yellow: np.ndarray, min_px: int = 25) -> list[tuple[int, int, int, int, int]]:
    h, w = yellow.shape
    visited = np.zeros((h, w), dtype=bool)
    comps: list[tuple[int, int, int, int, int]] = []
    ys, xs = np.where(yellow)
    for y0, x0 in zip(ys, xs, strict=False):
        if visited[y0, x0]:
            continue
        q: deque[tuple[int, int]] = deque([(int(y0), int(x0))])
        visited[y0, x0] = True
        cells: list[tuple[int, int]] = []
        while q:
            y, x = q.popleft()
            cells.append((y, x))
            for dy, dx in (
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and yellow[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    q.append((ny, nx))
        if len(cells) < min_px:
            continue
        yy = [c[0] for c in cells]
        xx = [c[1] for c in cells]
        comps.append((min(yy), max(yy), min(xx), max(xx), len(cells)))
    return comps


def _cluster_components(
    comps: list[tuple[int, int, int, int, int]], gap: int = 45
) -> list[tuple[int, int, int, int, int]]:
    n = len(comps)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        a, b = find(i), find(j)
        if a != b:
            parent[b] = a

    for i in range(n):
        for j in range(i + 1, n):
            yi0, yi1, xi0, xi1, _ = comps[i]
            yj0, yj1, xj0, xj1, _ = comps[j]
            if not (
                xi1 + gap < xj0
                or xj1 + gap < xi0
                or yi1 + gap < yj0
                or yj1 + gap < yi0
            ):
                union(i, j)
    groups: dict[int, list[tuple[int, int, int, int, int]]] = {}
    for i, c in enumerate(comps):
        groups.setdefault(find(i), []).append(c)
    clusters: list[tuple[int, int, int, int, int]] = []
    for g in groups.values():
        ymin = min(c[0] for c in g)
        ymax = max(c[1] for c in g)
        xmin = min(c[2] for c in g)
        xmax = max(c[3] for c in g)
        total = sum(c[4] for c in g)
        clusters.append((ymin, ymax, xmin, xmax, total))
    return clusters


def detect_shopmill(rgb: np.ndarray) -> DetectionResult:
    """Detect the ShopMill logo pattern on a studio product image."""
    h, w, _ = rgb.shape
    y2 = max(8, int(h * 0.16))
    x2 = max(8, int(w * 0.55))
    yellow = _yellow_mask(rgb, y2, x2)
    comps = _yellow_components(yellow)
    if not comps:
        return DetectionResult(
            False, None, "none", 0, 0, "none", reason="no_yellow_components"
        )
    clusters = _cluster_components(comps)
    cands = [
        c
        for c in clusters
        if c[0] < h * 0.12 and c[2] < w * 0.30 and c[4] >= 200
    ]
    if not cands:
        return DetectionResult(
            False,
            None,
            "low",
            int(yellow.sum()),
            0,
            "none",
            reason="no_top_left_cluster",
        )
    shop = max(cands, key=lambda c: c[4])
    y_ymin, y_ymax, y_xmin, y_xmax, yn = shop

    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    dark = (r < 85) & (g < 85) & (b < 110) & ((r + g + b) < 230)
    dark[: max(0, y_ymin - 25), :] = False
    dark[min(h, y_ymax + 40) :, :] = False
    dark[:, : max(0, y_xmax - 10)] = False
    dark[:, min(w, y_xmax + 300) :] = False
    dark_px = int(dark.sum())

    if dark_px < 20:
        xmin = max(0, y_xmin - 12)
        xmax = min(w - 1, y_xmax + int((y_xmax - y_xmin) * 1.2) + 24)
        ymin = max(0, y_ymin - 12)
        ymax = min(h - 1, y_ymax + 12)
        return DetectionResult(
            True,
            (xmin, ymin, xmax, ymax),
            "medium",
            yn,
            0,
            "shop_only",
            reason="yellow_cluster_without_dark_mill",
        )

    ds, dx = np.where(dark)
    d_ymin, d_ymax = int(ds.min()), int(ds.max())
    d_xmin, d_xmax = int(dx.min()), int(dx.max())
    xmin = max(0, min(y_xmin, d_xmin) - 14)
    xmax = min(w - 1, max(y_xmax, d_xmax) + 14)
    ymin = max(0, min(y_ymin, d_ymin) - 12)
    ymax = min(h - 1, max(y_ymax, d_ymax) + 12)
    if xmax - xmin > int(w * 0.40):
        xmax = min(w - 1, xmin + int(w * 0.36))
    return DetectionResult(
        True,
        (int(xmin), int(ymin), int(xmax), int(ymax)),
        "high",
        yn,
        dark_px,
        "yellow_dark",
    )


def detect_shopmill_file(path: Path) -> DetectionResult:
    return detect_shopmill(_load_rgb(path))


def remaining_logo_zone_yellow(rgb: np.ndarray) -> int:
    """Yellow px in the strict logo zone (top 10% × left 30%)."""
    h, w, _ = rgb.shape
    y2 = max(8, int(h * 0.10))
    x2 = max(8, int(w * 0.30))
    return int(_yellow_mask(rgb, y2, x2).sum())
