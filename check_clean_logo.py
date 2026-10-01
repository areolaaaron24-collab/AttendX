from PIL import Image

path = r"C:\SchoolAttendanceSystem\assets\AttendX_Logo_Clean.png"

img = Image.open(path).convert("RGBA")

print("SIZE:", img.size)
print("ALPHA:", img.getchannel("A").getextrema())

corners = [
    (0, 0),
    (img.width - 1, 0),
    (0, img.height - 1),
    (img.width - 1, img.height - 1)
]

print("\nCORNER COLORS:")

for point in corners:
    print(point, img.getpixel(point))

colors = {}

for pixel in img.getdata():
    r, g, b, a = pixel

    if a > 10:
        key = (
            round(r / 10) * 10,
            round(g / 10) * 10,
            round(b / 10) * 10
        )

        colors[key] = colors.get(key, 0) + 1

print("\nTOP COLORS:")

for color, count in sorted(
    colors.items(),
    key=lambda x: x[1],
    reverse=True
)[:15]:
    print(color, count)