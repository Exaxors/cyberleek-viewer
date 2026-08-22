"""Generate assets/icon.ico — an ode to the original CYBERLEEK favicon.

Built from the site's own mascot, framed like the site's hero section:
dark navy tile (#00050d), faint CRT grid, neon ring with glow (#0064ec),
green status dot (#60c33a) — the site's exact palette.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
MASCOT = Path(r"C:\Users\SIMP\Downloads\Cyberleek\CYBERLEEK_files\image-CgGkSufa.png")
OUT = ROOT / "assets" / "icon.ico"

BG = (0, 5, 13, 255)        # #00050d
NEON = (0, 100, 236, 255)   # #0064ec
GREEN = (96, 195, 58, 255)  # #60c33a
GRID = (0, 100, 236, 26)    # faint grid lines

S = 512   # master canvas
SS = 4    # supersample factor for anti-aliased shapes


def glow_layer(size: int, color: tuple, radius_frac: float, alpha: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pad = int(size * (1 - radius_frac) / 2)
    d.ellipse([pad, pad, size - pad, size - pad], fill=(*color[:3], alpha))
    return layer.filter(ImageFilter.GaussianBlur(size // 12))


def main() -> None:
    mascot = Image.open(MASCOT).convert("RGBA").resize((S, S), Image.LANCZOS)

    big = S * SS
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, big, big], fill=255)
    mask = mask.resize((S, S), Image.LANCZOS)

    canvas = Image.new("RGBA", (S, S), BG)

    grid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(grid)
    for i in range(1, 8):
        p = int(S * i / 8)
        d.line([(p, 0), (p, S)], fill=GRID, width=2)
        d.line([(0, p), (S, p)], fill=GRID, width=2)
    canvas.alpha_composite(grid)

    canvas.alpha_composite(glow_layer(S, NEON, 1.00, 60))
    canvas.alpha_composite(glow_layer(S, NEON, 0.92, 70))

    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(mascot, (0, 0), mask)
    canvas.alpha_composite(cut)

    ring = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring)
    m = big // 64
    dr.ellipse([m, m, big - m, big - m], outline=(*NEON[:3], 90), width=big // 28)
    dr.ellipse([m, m, big - m, big - m], outline=NEON, width=big // 96)
    canvas.alpha_composite(ring.resize((S, S), Image.LANCZOS))

    dot_r = S // 26
    cx, cy = int(S * 0.72), int(S * 0.28)
    glow_dot = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow_dot).ellipse(
        [cx - dot_r * 3, cy - dot_r * 3, cx + dot_r * 3, cy + dot_r * 3],
        fill=(*GREEN[:3], 80),
    )
    canvas.alpha_composite(glow_dot.filter(ImageFilter.GaussianBlur(dot_r)))
    crisp_dot = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(crisp_dot).ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=GREEN
    )
    canvas.alpha_composite(crisp_dot)

    rmask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(rmask).rounded_rectangle([0, 0, big, big], radius=big // 5, fill=255)
    rmask = rmask.resize((S, S), Image.LANCZOS)
    canvas.putalpha(
        Image.composite(canvas.getchannel("A"), Image.new("L", (S, S), 0), rmask)
    )

    OUT.parent.mkdir(exist_ok=True)
    canvas.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
