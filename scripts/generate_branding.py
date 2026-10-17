"""Reproducible, small-size-aware original branding (Pillow is build-time only)."""
from pathlib import Path
from PIL import Image, ImageDraw
import struct
import io

ROOT = Path(__file__).resolve().parents[1] / 'assets'
SIZES = (16, 24, 32, 48, 64, 128, 256)


def icon(size):
    scale = 4
    factor = size * scale / 256
    im = Image.new('RGBA', (size * scale, size * scale))
    d = ImageDraw.Draw(im)
    def box(coords): return tuple(round(x * factor) for x in coords)
    def line(points, fill, width):
        d.line([tuple(round(v * factor) for v in p) for p in points], fill=fill, width=max(1, round(width * factor)), joint='curve')
    d.rounded_rectangle(box((8, 8, 248, 248)), radius=round(53*factor), fill='#0c1730', outline='#375c9b', width=max(1, round(3*factor)))
    d.rounded_rectangle(box((25, 32, 163, 218)), radius=round(21*factor), fill='#714bf1')
    d.rounded_rectangle(box((38, 24, 174, 205)), radius=round(20*factor), fill='#2ba8e5')
    d.polygon([box(p) for p in [(53, 24), (141, 24), (181, 65), (181, 196), (53, 196)]], fill='#edf7ff')
    d.polygon([box(p) for p in [(140, 25), (140, 66), (180, 66)]], fill='#9cbee5')
    if size >= 24:
        line([(70, 85), (133, 85)], '#4076af', 9)
        line([(70, 106), (116, 106)], '#4076af', 9)
    # Open shackle: deliberate right-hand gap remains visible at 16px.
    d.arc(box((137, 84, 216, 166)), 165, 355, fill='#49e6ee', width=max(2, round(14*factor)))
    d.rounded_rectangle(box((110, 134, 231, 228)), radius=round(23*factor), fill='#3167ec', outline='#65f0f1', width=max(1,round(5*factor)))
    d.ellipse(box((158, 158, 184, 184)), fill='#f1fbff')
    d.polygon([box(p) for p in [(165, 176), (177, 176), (182, 202), (160, 202)]], fill='#f1fbff')
    return im.resize((size,size), Image.Resampling.LANCZOS)


def main():
    ROOT.mkdir(exist_ok=True)
    images = {s:icon(s) for s in SIZES}
    # ICO directory explicitly includes every size, each independently drawn.
    payloads=[]
    for im in images.values():
        output=io.BytesIO(); im.save(output,format='PNG'); payloads.append(output.getvalue())
    offset=6+16*len(SIZES)
    headers=[]
    for s,data in zip(SIZES,payloads):
        headers.append(struct.pack('<BBBBHHII',s if s<256 else 0,s if s<256 else 0,0,0,1,32,len(data),offset))
        offset+=len(data)
    (ROOT/'app.ico').write_bytes(struct.pack('<HHH',0,1,len(SIZES))+b''.join(headers)+b''.join(payloads))
    for s in (32,48,64,128,256):images[s].save(ROOT/f'app-{s}.png')
    # Matching vector master for documentation and future edits.
    (ROOT/'app.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
<rect x="8" y="8" width="240" height="240" rx="53" fill="#0c1730" stroke="#375c9b" stroke-width="3"/>
<rect x="25" y="32" width="138" height="186" rx="21" fill="#714bf1"/>
<rect x="38" y="24" width="136" height="181" rx="20" fill="#2ba8e5"/>
<path d="M53 24h88l40 41v131H53z" fill="#edf7ff"/><path d="M140 25v41h40z" fill="#9cbee5"/>
<path d="M70 85h63M70 106h46" fill="none" stroke="#4076af" stroke-width="9"/>
<path d="M138 145v-20a39 39 0 0 1 78 0" fill="none" stroke="#49e6ee" stroke-width="14"/>
<rect x="110" y="134" width="121" height="94" rx="23" fill="#3167ec" stroke="#65f0f1" stroke-width="5"/>
<circle cx="171" cy="171" r="13" fill="#f1fbff"/><path d="M165 176h12l5 26h-22z" fill="#f1fbff"/>
</svg>''',encoding='utf-8')
    # Native Inno Setup wizard images, with no third-party marks.
    for name,size in [('wizard.bmp',(164,314)),('wizard-small.bmp',(55,55))]:
        bg=Image.new('RGB',size,'#0b1325')
        mark=icon(120 if size[0]>100 else 48)
        bg.paste(mark,((size[0]-mark.width)//2,40 if size[0]>100 else 3),mark)
        if size[0]>100:
            draw=ImageDraw.Draw(bg)
            draw.rectangle((26,205,138,208), fill='#45ddeb')
            draw.rectangle((26,218,108,220), fill='#7864ed')
        bg.save(ROOT/name)
    print('Generated ICO sizes:', ', '.join(map(str,SIZES)))

if __name__=='__main__':main()
