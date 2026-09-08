def simple_pdf(lines: list[str]) -> bytes:
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:110] for line in lines]
    text = "BT /F1 10 Tf 50 790 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in escaped) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(text.encode())} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body, offsets = "%PDF-1.4\n", [0]
    for number, item in enumerate(objects, 1):
        offsets.append(len(body.encode()))
        body += f"{number} 0 obj\n{item}\nendobj\n"
    xref = len(body.encode())
    body += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n" + "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    body += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return body.encode()
