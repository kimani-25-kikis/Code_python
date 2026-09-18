from PIL import Image
import sys

def image_to_ascii(path, width=100):
    chars = "@%#*+=-:. "
    img = Image.open(path).convert("L")
    aspect = img.height / img.width
    height = int(width * aspect * 0.5)
    img = img.resize((width, height))
    pixels = img.getdata()
    ascii_str = "".join(chars[p * len(chars) // 256] for p in pixels)
    return "\n".join(ascii_str[i:i+width] for i in range(0, len(ascii_str), width))

if __name__ == "__main__":
    print(image_to_ascii(sys.argv[1]))