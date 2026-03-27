"""Çizim algoritmaları — Bresenham çizgi ve BFS tabanlı flood fill."""

import numpy as np
from collections import deque


def bresenham_line(x0, y0, x1, y1):
    """Fırça atlamasını önleyen matematiksel çizgi interpolasyonu."""
    points = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def flood_fill(grid, x, y, target, replacement):
    """Stack-overflow'u engelleyen üretim kalite kuyruk BFS boya kovası."""
    h, w = grid.shape
    if target == replacement:
        return None, None

    mask = np.zeros((h, w), dtype=bool)
    q = deque([(x, y)])
    mask[y, x] = True
    min_x = max_x = x
    min_y = max_y = y

    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h and not mask[ny, nx] and grid[ny, nx] == target:
                mask[ny, nx] = True
                q.append((nx, ny))
                if nx < min_x:
                    min_x = nx
                if nx > max_x:
                    max_x = nx
                if ny < min_y:
                    min_y = ny
                if ny > max_y:
                    max_y = ny

    bbox = (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return mask, bbox
