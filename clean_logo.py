from PIL import Image

input_path = r"C:\SchoolAttendanceSystem\assets\AttendX_Logo.png"
output_path = r"C:\SchoolAttendanceSystem\assets\AttendX_Logo_Clean.png"

img = Image.open(input_path).convert("RGBA")

pixels = img.load()
width, height = img.size

for y in range(height):
    for x in range(width):
        r, g, b, a = pixels[x, y]

        brightness = (r + g + b) / 3

        if brightness < 35:
            pixels[x, y] = (r, g, b, 0)

img.save(output_path)

print("Done!")
print("Saved:", output_path)