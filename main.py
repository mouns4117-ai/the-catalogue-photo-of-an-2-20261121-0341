#!/usr/bin/env python3
"""Catalogue photograph of an impossible gadget, drawn by hand.

The program renders a studio product shot of the LEVIT-TEA 3000, a
self-pouring teapot that floats above its cup while the tea streams
UPWARD from the cup into the spout. Pure Python 3.13 standard library:
a small rasterizer plus a hand-rolled PNG encoder. Deterministic:
the same bytes on every run.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024


def _chunk(kind, data):
    body = struct.pack(">I", len(data)) + kind + data
    return body + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode_png(rgb, w, h):
    """Encode an RGB bytearray as a PNG (filter 0, zlib level 6)."""
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 6)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


def lerp(a, b, t):
    return int(a + (b - a) * t + 0.5)


def mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


class Canvas:
    def __init__(self, w, h, base=(240, 239, 235)):
        self.w = w
        self.h = h
        self.px = bytearray(base * (w * h))

    def put(self, x, y, color, alpha=1.0):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        if alpha >= 1.0:
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]
        else:
            inv = 1.0 - alpha
            self.px[i] = int(color[0] * alpha + self.px[i] * inv + 0.5)
            self.px[i + 1] = int(color[1] * alpha + self.px[i + 1] * inv + 0.5)
            self.px[i + 2] = int(color[2] * alpha + self.px[i + 2] * inv + 0.5)

    def vgrad(self, top, bottom):
        for y in range(self.h):
            t = y / (self.h - 1)
            c = mix(top, bottom, t)
            row = y * self.w * 3
            for x in range(self.w):
                i = row + x * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.put(x, y, color, alpha)

    def disc(self, cx, cy, r, color, alpha=1.0):
        r2 = r * r
        for y in range(int(cy - r), int(cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0.0, r2 - dy * dy)))
            for x in range(int(cx - dx), int(cx + dx) + 1):
                self.put(x, y, color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, grad=None):
        """Filled ellipse; grad=(top_color, bottom_color) gives a vertical
        gradient clipped to the ellipse."""
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1.0:
                continue
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            c = color
            if grad is not None:
                t = (y - (cy - ry)) / (2.0 * ry)
                c = mix(grad[0], grad[1], t)
            for x in range(int(cx - dx), int(cx + dx) + 1):
                self.put(x, y, c, alpha)

    def soft_ellipse(self, cx, cy, rx, ry, color, alpha, steps=7):
        """Blurred shadow: nested ellipses fading outward."""
        for s in range(steps, 0, -1):
            f = s / steps
            self.ellipse(cx, cy, rx * f, ry * f, color,
                         alpha * (1.0 - f) * 0.9 + 0.02)

    def poly(self, pts, color, alpha=1.0, grad=None):
        """Scanline-filled polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = pts[i]
                x1, y1p = pts[(i + 1) % n]
                if (y0p <= y < y1p) or (y1p <= y < y0p):
                    t = (y - y0p) / (y1p - y0p)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            c = color
            if grad is not None:
                t = (y - y0) / max(1, y1 - y0)
                c = mix(grad[0], grad[1], t)
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.put(x, y, c, alpha)

    def thick_line(self, x0, y0, x1, y1, r, color, alpha=1.0):
        """A line drawn as a chain of discs (round caps)."""
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(dist / max(1.0, r * 0.5)))
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, color, alpha)

    def bezier(self, p0, p1, p2, p3, r0, r1, color, alpha=1.0, steps=48):
        """Cubic bezier drawn as tapering discs (r0 -> r1)."""
        prev = None
        for s in range(steps + 1):
            t = s / steps
            mt = 1.0 - t
            x = (mt ** 3) * p0[0] + 3 * mt * mt * t * p1[0] \
                + 3 * mt * t * t * p2[0] + (t ** 3) * p3[0]
            y = (mt ** 3) * p0[1] + 3 * mt * mt * t * p1[1] \
                + 3 * mt * t * t * p2[1] + (t ** 3) * p3[1]
            r = r0 + (r1 - r0) * t
            if prev is not None:
                self.thick_line(prev[0], prev[1], x, y, r, color, alpha)
            prev = (x, y)


def rounded_rect(cv, x0, y0, x1, y1, r, color, alpha=1.0, grad=None):
    """Rectangle with rounded corners."""
    cv.rect(x0 + r, y0, x1 - r, y1, color, alpha)
    cv.rect(x0, y0 + r, x1, y1 - r, color, alpha)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                   (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv.disc(cx, cy, r, color, alpha)
    if grad is not None:
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0)
            c = mix(grad[0], grad[1], t)
            for x in range(x0, x1):
                # only recolour inside the rounded shape: skip corners
                if (x < x0 + r and y < y0 + r
                        and (x - (x0 + r)) ** 2 + (y - (y0 + r)) ** 2 > r * r):
                    continue
                if (x > x1 - r and y < y0 + r
                        and (x - (x1 - r)) ** 2 + (y - (y0 + r)) ** 2 > r * r):
                    continue
                if (x < x0 + r and y > y1 - r
                        and (x - (x0 + r)) ** 2 + (y - (y1 - r)) ** 2 > r * r):
                    continue
                if (x > x1 - r and y > y1 - r
                        and (x - (x1 - r)) ** 2 + (y - (y1 - r)) ** 2 > r * r):
                    continue
                cv.put(x, y, c, alpha)


# ---------------------------------------------------------------- scene ----
# Palette: warm studio neutrals, brushed steel teapot, amber tea.
STEEL_TOP = (176, 196, 212)
STEEL_BOT = (104, 126, 146)
STEEL_DARK = (82, 100, 118)
KNOB = (58, 74, 90)
TEA = (178, 112, 38)
TEA_HI = (228, 168, 78)
CUP = (250, 249, 246)
CUP_SHADE = (222, 221, 217)
SHADOW = (40, 36, 30)


def draw_scene(cv):
    # Studio backdrop: soft vertical gradient + central glow.
    cv.vgrad((246, 245, 241), (210, 208, 201))
    cv.soft_ellipse(512, 430, 470, 380, (255, 255, 250), 0.35, steps=9)
    # Floor: a faint horizon and a slightly darker lower band.
    cv.rect(0, 782, W, 800, (196, 193, 186), 0.55)
    cv.rect(0, 800, W, H, (198, 195, 188), 0.35)

    # Soft shadows on the floor (teapot floats, so its shadow is
    # detached and fainter than the cup's).
    cv.soft_ellipse(512, 812, 190, 22, SHADOW, 0.16, steps=8)
    cv.soft_ellipse(512, 826, 150, 16, SHADOW, 0.30, steps=8)

    # ---- cup and saucer (the one accessory) ----
    # Saucer.
    cv.ellipse(512, 812, 158, 24, CUP_SHADE)
    cv.ellipse(512, 808, 158, 22, CUP)
    cv.ellipse(512, 808, 120, 16, CUP_SHADE, 0.5)
    # Cup body: tapered sides, rounded base.
    cv.poly([(438, 706), (586, 706), (572, 798), (452, 798)], CUP,
            grad=(CUP, CUP_SHADE))
    cv.ellipse(512, 706, 74, 12, (238, 237, 233))
    # Tea surface inside the cup.
    cv.ellipse(512, 707, 62, 9, TEA)
    cv.ellipse(508, 706, 34, 5, TEA_HI, 0.7)
    # Cup handle (right side).
    cv.thick_line(580, 724, 612, 736, 9, CUP)
    cv.thick_line(612, 736, 606, 766, 9, CUP)
    cv.thick_line(606, 766, 576, 776, 9, CUP)
    # Cup highlight stripe.
    cv.thick_line(462, 716, 470, 786, 7, (255, 255, 255), 0.55)

    # ---- the impossible stream: tea rising from the cup to the spout ----
    # Main rising arc, tapering as it climbs.
    cv.bezier((556, 700), (660, 560), (742, 430), (788, 316),
              11, 5, TEA, 0.95)
    # Bright thread inside the stream.
    cv.bezier((550, 698), (648, 556), (728, 428), (780, 318),
              4, 2, TEA_HI, 0.85)
    # Droplets breaking away from the stream, climbing with it.
    for (dx, dy, dr) in ((700, 500, 7), (742, 436, 6), (766, 372, 5),
                         (636, 596, 6), (596, 648, 5)):
        cv.disc(dx, dy, dr, TEA, 0.95)
        cv.disc(dx - 2, dy - 2, max(1, dr // 3), TEA_HI, 0.9)

    # ---- teapot (floating: no contact with the floor) ----
    # Handle: a bold C-curve on the left.
    cv.thick_line(344, 392, 292, 420, 16, STEEL_DARK)
    cv.thick_line(292, 420, 296, 486, 16, STEEL_DARK)
    cv.thick_line(296, 486, 352, 500, 16, STEEL_DARK)
    cv.thick_line(352, 392, 306, 414, 7, STEEL_TOP, 0.8)
    # Spout: rising from the body to the upper right, tip catching
    # the stream.
    cv.bezier((664, 470), (742, 430), (782, 372), (796, 312),
              26, 12, STEEL_DARK)
    cv.bezier((668, 458), (736, 420), (772, 366), (786, 314),
              16, 7, STEEL_TOP, 0.9)
    # Body: a wide steel belly with a vertical gradient.
    cv.ellipse(512, 448, 196, 138, STEEL_BOT,
               grad=(STEEL_TOP, STEEL_BOT))
    # Belly highlight: a soft white sheen upper-left.
    cv.ellipse(452, 400, 84, 46, (255, 255, 255), 0.38)
    cv.ellipse(452, 392, 46, 24, (255, 255, 255), 0.30)
    # Lower shade for roundness.
    cv.ellipse(540, 540, 150, 34, STEEL_DARK, 0.25)
    # Lid and knob.
    cv.ellipse(512, 322, 104, 30, STEEL_DARK, grad=(STEEL_TOP, STEEL_DARK))
    cv.ellipse(512, 312, 88, 20, STEEL_TOP, 0.9)
    cv.disc(512, 296, 20, KNOB)
    cv.disc(506, 290, 7, (140, 158, 176), 0.9)
    # Brand plate on the belly: a small dark plate with a light stripe.
    rounded_rect(cv, 468, 452, 556, 486, 10, (52, 66, 80), 0.95)
    cv.rect(482, 464, 542, 472, (196, 210, 222), 0.9)


def main():
    cv = Canvas(W, H)
    draw_scene(cv)
    os.makedirs("/output", exist_ok=True)
    with open("/output/entry.png", "wb") as f:
        f.write(encode_png(cv.px, W, H))


if __name__ == "__main__":
    main()
