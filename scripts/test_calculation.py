#!/usr/bin/env python3
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from utils.scene_calculations import calculate_eighths_from_pages, format_eighths

# Test the calculation for Die Testament scenes
print("Testing page-based calculation:\n")

# Scene 1: Page 4-4 (1 page)
scene1 = calculate_eighths_from_pages(4, 4)
print(f"Scene 1 (pages 4-4): {scene1} eighths = {format_eighths(scene1)}")

# Scene 2: Pages 4-6 (3 pages)
scene2 = calculate_eighths_from_pages(4, 6)
print(f"Scene 2 (pages 4-6): {scene2} eighths = {format_eighths(scene2)}")

# Scene 3: Pages 6-7 (2 pages)
scene3 = calculate_eighths_from_pages(6, 7)
print(f"Scene 3 (pages 6-7): {scene3} eighths = {format_eighths(scene3)}")

total = scene1 + scene2 + scene3
print(f"\nTotal: {total} eighths = {format_eighths(total)} = {total/8:.1f} pages")
