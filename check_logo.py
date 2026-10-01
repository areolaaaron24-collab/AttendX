from PIL import Image

path = r"C:\SchoolAttendanceSystem\assets\AttendX_Logo.png"

img = Image.open(path).convert("RGBA")

print("Image size:", img.size)

alpha = img.getchannel("A")

print("Alpha minimum:", alpha.getextrema()[0])
print("Alpha maximum:", alpha.getextrema()[1])

transparent = 0
visible = 0

for value in alpha.getdata():
    if value == 0:
        transparent += 1
    else:
        visible += 1

print("Transparent pixels:", transparent)
print("Visible pixels:", visible)

total = img.width * img.height

print("Total pixels:", total)
print("Visible percentage:", round((visible / total) * 100, 2), "%")