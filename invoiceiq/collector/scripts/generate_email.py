from email.message import EmailMessage

# Create the email message
msg = EmailMessage()
msg["From"] = "finance@bioplex.com"
msg["To"] = "ap@snowflake.com"
msg["Subject"] = "Invoice #BPXINV-00550"
msg["MIME-Version"] = "1.0"

# Add plain text and HTML versions
plain_text = "Please find the monthly bill attached."
html_text = """\
<html>
  <body>
    <p>Please find the monthly bill attached.</p>
  </body>
</html>
"""

# Add both versions (this creates a multipart/alternative section)
msg.set_content(plain_text)
msg.add_alternative(html_text, subtype="html")

# Add a binary attachment
binary_data = b"%PDF-1.4\n%fake pdf content\n%%EOF"
msg.add_attachment(binary_data, maintype="application", subtype="octet-stream", filename="invoice_01.pdf")

# Write to file
out = "example_email.eml"
with open(out, "wb") as f:
    f.write(bytes(msg))

print(f"✅ {out} created successfully!")
