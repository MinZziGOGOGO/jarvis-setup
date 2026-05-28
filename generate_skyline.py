"""
Generate city skyline silhouette PNG assets with animated window lights.
Standalone script — run once to produce all assets.
"""
import os
import random
from PIL import Image, ImageFilter

from config import SKYLINE_WIDTH, SKYLINE_HEIGHT


def generate_skyline(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # ── Seeded building shapes (identical across all frames) ──
    rng = random.Random(42)  # Fixed seed for reproducible building shapes
    buildings = []
    x = 0
    while x < SKYLINE_WIDTH:
        w = rng.randint(30, 80)
        h = rng.randint(50, 250)
        buildings.append({"x": x, "w": w, "h": h})
        x += w + rng.randint(2, 5)

    # Window positions per building (deterministic)
    all_windows = []
    for b in buildings:
        bx, bw, bh = b["x"], b["w"], b["h"]
        win_count = rng.randint(1, max(1, (bw * bh) // 800))
        for _ in range(win_count):
            wx = bx + rng.randint(2, bw - 4)
            wy = SKYLINE_HEIGHT - bh + rng.randint(5, bh - 7)
            all_windows.append((wx, wy))

    # ── Generate frames ──
    # Build base silhouette (dark buildings, no windows)
    base = Image.new("RGBA", (SKYLINE_WIDTH, SKYLINE_HEIGHT), (0, 0, 0, 0))
    for b in buildings:
        for x in range(b["x"], b["x"] + b["w"] + 1):
            if x < 0 or x >= SKYLINE_WIDTH:
                continue
            for y in range(max(0, SKYLINE_HEIGHT - b["h"]), SKYLINE_HEIGHT):
                base.putpixel((x, y), (10, 0, 15, 255))

    # Apply Gaussian blur
    base = base.filter(ImageFilter.GaussianBlur(radius=8))

    # Save main image
    base.save(os.path.join(output_dir, "city_skyline.png"))

    # Generate 10 frame variants with different lit windows
    frame_rng = random.Random(123)
    for frame_idx in range(1, 11):
        frame = base.copy()
        # Decide which windows are lit (~40-60% lit per frame)
        lit_count = int(len(all_windows) * frame_rng.uniform(0.4, 0.6))
        lit_indices = set(frame_rng.sample(range(len(all_windows)), lit_count))

        for i, (wx, wy) in enumerate(all_windows):
            if i in lit_indices:
                color = (0, 255, 255, 220) if frame_rng.random() < 0.6 else (255, 45, 155, 220)
                # Draw 2x3 window rect
                for dx in range(2):
                    for dy in range(3):
                        px, py = wx + dx, wy + dy
                        if 0 <= px < SKYLINE_WIDTH and 0 <= py < SKYLINE_HEIGHT:
                            frame.putpixel((px, py), color)

        frame.save(os.path.join(output_dir, f"city_skyline_{frame_idx:02d}.png"))
        print(f"  Saved city_skyline_{frame_idx:02d}.png")


if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    print(f"Generating skyline assets in {assets_dir}...")
    generate_skyline(assets_dir)
    print("Done! Generated city_skyline.png + 10 frame variants.")
