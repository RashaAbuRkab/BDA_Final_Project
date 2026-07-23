# create_test_pdf.py
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

width, height = A4

# ============================================
# الصورة 1: جدول بيانات (كصورة)
# ============================================
fig, ax = plt.subplots(figsize=(6, 3))
ax.axis("off")
table_data = [
    ["Month", "Sales ($)", "Units"],
    ["January", "12,400", "310"],
    ["February", "15,800", "395"],
    ["March", "21,150", "528"],
    ["April", "18,900", "472"],
]
table = ax.table(cellText=table_data, loc="center", cellLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2)
plt.tight_layout()
plt.savefig("table_image.png", dpi=150, bbox_inches="tight")
plt.close()

# ============================================
# الصورة 2: "صفحة ممسوحة ضوئيًا" (نص كصورة بالكامل)
# ننشئها كصورة فيها نص، بدون أي طبقة نص رقمي
# ============================================
scanned_img = Image.new("RGB", (1000, 700), color="white")
from PIL import ImageDraw, ImageFont
draw = ImageDraw.Draw(scanned_img)
try:
    font = ImageFont.truetype("arial.ttf", 28)
except:
    font = ImageFont.load_default()

lines = [
    "CONFIDENTIAL MEMO",
    "",
    "Project Code: PX-2091",
    "Approval Status: Approved",
    "Budget Allocated: $84,500",
    "Approved by: J. Anderson",
    "Date: March 15, 2024",
]
y = 40
for line in lines:
    draw.text((40, y), line, fill="black", font=font)
    y += 60

scanned_img.save("scanned_page.png")

# ============================================
# بناء ملف PDF النهائي
# ============================================
c = canvas.Canvas("test_multimodal.pdf", pagesize=A4)

# --- صفحة 1: نص عادي فقط ---
c.setFont("Helvetica-Bold", 16)
c.drawString(50, height - 50, "Quarterly Business Report")
c.setFont("Helvetica", 11)
c.drawString(50, height - 90, "This report contains our latest performance data.")
c.drawString(50, height - 110, "Please refer to the following pages for details.")
c.showPage()

# --- صفحة 2: جدول كصورة (بدون أي نص رقمي حوله) ---
img1 = ImageReader("table_image.png")
c.drawImage(img1, 50, height - 350, width=450, height=220, preserveAspectRatio=True)
c.showPage()

# --- صفحة 3: صفحة "ممسوحة" بالكامل (صورة فقط، بدون نص رقمي إطلاقًا) ---
img2 = ImageReader("scanned_page.png")
c.drawImage(img2, 0, 0, width=width, height=height, preserveAspectRatio=False)
c.showPage()

c.save()
print("Done: test_multimodal.pdf")