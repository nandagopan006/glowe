from PIL import Image

def resize_image(image_path):
    img =Image.open(image_path)

    if img.mode !='RGB':
        img =img.convert('RGB')
    #Resize
    img =img.resize((800, 800))
    img.save(image_path)