from PIL import Image

png = Image.open("icon.png").convert("RGBA")
sizes = [16, 24, 32, 48, 64, 128, 256]
png.save("icon.ico", sizes=[(s, s) for s in sizes])
print("icon.ico written with sizes:", sizes)
