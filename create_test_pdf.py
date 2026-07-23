# create_test_pdf.py
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# #1) Create an image (graph) containing a specific number/information not mentioned as text
fig, ax = plt.subplots(figsize=(5, 3))
categories = ["Q1", "Q2", "Q3", "Q4"]
values = [120, 340, 275, 410]
ax.bar(categories, values, color="teal")
ax.set_title("Quarterly Revenue (in $1000)")
ax.set_ylabel("Revenue")
plt.tight_layout()
plt.savefig("chart.png", dpi=150)
plt.close()

#2) Create a PDF containing plain text + an embedded image
c = canvas.Canvas("test_with_image.pdf", pagesize=A4)
width, height = A4

c.setFont("Helvetica-Bold", 16)
c.drawString(50, height - 50, "Company Performance Report")

c.setFont("Helvetica", 11)
c.drawString(50, height - 90, "This report summarizes our performance for the fiscal year.")
c.drawString(50, height - 110, "Please refer to the chart below for quarterly figures.")

# Insert image
img = ImageReader("chart.png")
c.drawImage(img, 50, height - 400, width=400, height=240)

c.save()
print("Done: test_with_image.pdf")