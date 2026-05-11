from PIL import Image
import pytesseract
import sys

try:
    img = Image.open('wear_screenshot2.png')
    text = pytesseract.image_to_string(img)
    print("OCR text:")
    print(text)
    
    # Check colors
    colors = img.getcolors(maxcolors=1000000)
    colors = sorted(colors, reverse=True)
    print("Top 5 colors:")
    for c in colors[:5]:
        print(c)
except Exception as e:
    print(e)
