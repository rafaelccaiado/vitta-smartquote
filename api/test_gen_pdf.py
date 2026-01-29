import fitz

doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "Hemograma Completo\nGlicose Jejum\nDr. Teste 123", fontsize=20)
doc.save("test_payload.pdf")
print("PDF Saved.")
