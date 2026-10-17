"""Compare the actual Windows resource pixels with the committed 32px icon."""
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
expected=Image.open(root/'assets/app-32.png').convert('RGBA')
for name in ('installed-exe-icon.png','installer-icon.png','uninstaller-icon.png'):
    actual=Image.open(root/'qa/screenshots'/name).convert('RGBA')
    if actual.size!=expected.size or actual.tobytes()!=expected.tobytes():raise AssertionError(f'Icon resource differs: {name}')
    print(f'Pixel-identical branding: {name}')
