from PIL import Image
import os

def convert_to_ico():
    # Load the PNG image
    img = Image.open("Process Monitor Icon.png")
    
    # Prepare different sizes for the ico
    icon_sizes = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
    icons = []
    
    # Create each size
    for size in icon_sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save as ICO file
    icons[0].save('app_icon.ico', format='ICO', sizes=icon_sizes)

if __name__ == "__main__":
    convert_to_ico() 