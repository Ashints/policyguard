from pypdf import PdfReader

pdf_path = r"C:\Users\pc\Desktop\Projects\policyguard\data\raw\gdpr\articles.pdf"

reader = PdfReader(pdf_path)

print("Number of pages:", len(reader.pages))

text = reader.pages[0].extract_text()
print("First 500 characters:")
print(text[:500] if text else "❌ No text extracted")
