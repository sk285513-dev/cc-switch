import os, pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
files = ['media_1785946436952.png', 'media_1785946437071.png', 'media_1785933728773.png', 'media_1785933728789.png', 'media_1785925839377.png']
out = ''

for f in files:
    path = rf'C:\Users\temp\.gemini\antigravity\brain\81e392d6-0b96-48b6-ad8a-585c30054413\.user_uploaded\{f}'
    if os.path.exists(path):
        out += f'=== {f} ===\n'
        out += pytesseract.image_to_string(Image.open(path), lang='eng+chi_tra') + '\n'

with open('ocr_results.txt', 'w', encoding='utf-8') as file:
    file.write(out)
