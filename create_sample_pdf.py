"""Create a small, local PDF for the RAG practice notebooks.

Run with: .\\venv\\Scripts\\python.exe create_sample_pdf.py
"""

from pathlib import Path


OUTPUT_PATH = Path("your_document.pdf")

PAGES = [
    [
        "Greenfield Institute - Admission and Fee Policy",
        "",
        "Admissions",
        "Students confirm admission by paying the first-semester fee within 10 days of receiving an offer.",
        "The admission confirmation fee is INR 5,000 and is included in the first-semester fee.",
        "",
        "Cancellation and fee refunds",
        "A student who cancels admission within 7 calendar days of payment receives a full refund, minus the INR 500 processing fee.",
        "A student who cancels from day 8 through day 30 receives a 75 percent refund of tuition fees. The admission confirmation fee is not refunded.",
        "No tuition fee refund is available after 30 calendar days, except where the institute cancels the course.",
        "Refund requests must be submitted through the Student Portal with the payment receipt and cancellation form.",
    ],
    [
        "Greenfield Institute - Student Services",
        "",
        "Refund processing",
        "The Finance Office processes complete refund requests within 10 working days.",
        "Refunds are issued to the original payment method. Bank transfers can take an additional 3 to 5 working days.",
        "Students can check their refund status in the Student Portal under Payments and Refunds.",
        "",
        "Contact",
        "For admission questions, email admissions@greenfield.example or call 1800-555-0142 from Monday to Friday, 9:00 AM to 5:00 PM.",
        "For technical portal issues, email support@greenfield.example.",
        "",
        "This sample document is fictional and exists only for local RAG practice.",
    ],
]


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 12 Tf", "72 760 Td", "15 TL"]
    for line in lines:
        commands.append(f"({escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1")


def build_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []
    page_ids = [4 + index * 2 for index in range(len(pages))]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(pages)} >>".encode()
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_id, lines in zip(page_ids, pages):
        stream_id = page_id + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode()
        )
        stream = page_stream(lines)
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


if __name__ == "__main__":
    OUTPUT_PATH.write_bytes(build_pdf(PAGES))
    print(f"Created {OUTPUT_PATH.resolve()}")
