from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size):
    img = Image.new('RGBA', (size, size), (26, 26, 46, 255))
    draw = ImageDraw.Draw(img)
    # Draw a simple "CB" text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(size * 0.4))
    except:
        font = ImageFont.load_default()
    draw.text((size//2, size//2), "CB", fill=(255, 153, 0, 255), font=font, anchor="mm")
    return img

for s in [16, 48, 128]:
    create_icon(s).save(f'icon{s}.png')
    print(f'Created icon{s}.png')
