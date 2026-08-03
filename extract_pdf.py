"""
extract_pdf.py
--------------
استخراج النص من كتاب طبي بصيغة PDF، صفحة بصفحة أو فصل بفصل،
تمهيداً لتمريره لـ main.py.

الاستعمال:
    python extract_pdf.py --pdf book.pdf --start 10 --end 25 --output chapter1.txt
"""

import argparse
import fitz  # PyMuPDF


def extract_text(pdf_path: str, start_page: int = 0, end_page: int = None) -> str:
    doc = fitz.open(pdf_path)
    end_page = end_page or len(doc)

    text_parts = []
    for page_num in range(start_page, min(end_page, len(doc))):
        page = doc[page_num]
        text_parts.append(page.get_text())

    doc.close()
    return "\n".join(text_parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="استخراج نص من PDF طبي")
    parser.add_argument("--pdf", required=True, help="مسار ملف الـ PDF")
    parser.add_argument("--start", type=int, default=0, help="رقم الصفحة الأولى (0-indexed)")
    parser.add_argument("--end", type=int, default=None, help="رقم الصفحة الأخيرة (غير شامل)")
    parser.add_argument("--output", type=str, default="extracted.txt")
    args = parser.parse_args()

    text = extract_text(args.pdf, args.start, args.end)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"[DONE] تم استخراج {len(text.split())} كلمة تقريباً إلى: {args.output}")
