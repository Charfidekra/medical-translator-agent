import io
import gc
from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
import streamlit as st
from PIL import Image
from main import translate_document

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def process_single_page(args):
    """معالجة صفحة واحدة (استخراج + ترجمة)"""
    page_num, page_bytes, translator_func = args
    doc = fitz.open(stream=page_bytes, filetype="pdf")
    orig_page = doc[0]

    # 1. استخراج النص M
    extracted_text = orig_page.get_text("text").strip()
    
    pix = orig_page.get_pixmap(dpi=120)
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

    # 2. الترجمة
    if extracted_text:
        translated_text = translator_func(extracted_text)
    else:
        translated_text = "No selectable text found on this page."

    doc.close()
    return page_num, translated_text, img_pil, orig_page.rect.width, orig_page.rect.height


def generate_side_by_side_pdf_fast(uploaded_file, translator_func):
    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(orig_doc)

    # تحضير المهام للتوازي
    tasks = []
    for page_num in range(total_pages):
        # استخراج الصفحة كـ PDF مستقل صغير
        single_doc = fitz.open()
        single_doc.insert_pdf(orig_doc, from_page=page_num, to_page=page_num)
        page_bytes = single_doc.write()
        single_doc.close()
        tasks.append((page_num, page_bytes, translator_func))

    orig_doc.close()

    # شريط تقدم تفاعلي يريح المستخدم
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("🚀 جاري معالجة وصفحات الملف بالتوازي...")

    results = [None] * total_pages

    # تنفيذ الترجمة لجميع الصفحات بالتوازي (Parallel Execution)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_page, task) for task in tasks]
        completed = 0
        for future in futures:
            p_num, trans_text, img_pil, width, height = future.result()
            results[p_num] = (trans_text, img_pil, width, height)
            completed += 1
            progress_bar.progress(completed / total_pages)
            status_text.text(f"⚡ تم إكمال ترجمة {completed} من أصل {total_pages} صفحات...")

    status_text.text("🎨 جاري تجميع المستند النهائي...")

    # بناء ملف الـ PDF النهائي
    new_doc = fitz.open()
    all_translated_texts = []

    for page_num, (translated_text, final_img_pil, half_width, page_height) in enumerate(results):
        all_translated_texts.append(f"--- Page {page_num + 1} ---\n{translated_text}")

        buffer = io.BytesIO()
        doc_temp = SimpleDocTemplate(
            buffer,
            pagesize=(half_width, page_height),
            rightMargin=18,
            leftMargin=18,
            topMargin=20,
            bottomMargin=20,
        )

        styles = getSampleStyleSheet()
        
        watermark_style = ParagraphStyle(
            "WatermarkStyle", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=7, textColor="#777777", alignment=1, spaceAfter=4
        )
        title_style = ParagraphStyle(
            "SideTitleStyle", parent=styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=10, spaceAfter=6
        )

        # حساب حجم الخط تلقائياً ليطابق المساحة
        char_count = len(translated_text)
        f_size = 7 if char_count > 1500 else (8 if char_count > 800 else 9)
        leading = f_size + 3

        dynamic_style = ParagraphStyle(
            "DynamicStyle", parent=styles["Normal"],
            fontName="Helvetica", fontSize=f_size, leading=leading, spaceAfter=4
        )

        story = [
            Paragraph("— TRANSLATED BY MEDICAL TRANSLATOR AGENT —", watermark_style),
            Paragraph("BY DEKRA CHARFI", watermark_style),
            Spacer(1, 4),
            Paragraph(f"--- Translation Page {page_num + 1} ---", title_style)
        ]

        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, dynamic_style))
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 6))
        story.append(Paragraph("BY DEKRA CHARFI", watermark_style))

        doc_temp.build(story)
        buffer.seek(0)

        total_width = half_width * 2
        combo_page = new_doc.new_page(width=total_width, height=page_height)

        img_byte_arr = io.BytesIO()
        final_img_pil.save(img_byte_arr, format="PNG")
        combo_page.insert_image(
            fitz.Rect(0, 0, half_width, page_height),
            stream=img_byte_arr.getvalue()
        )

        translated_pdf_doc = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        combo_page.show_pdf_page(
            fitz.Rect(half_width, 0, total_width, page_height),
            translated_pdf_doc, 0
        )

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()

    progress_bar.empty()
    status_text.empty()

    output_buffer.seek(0)
    full_text_combined = "\n\n".join(all_translated_texts)
    return output_buffer.getvalue(), full_text_combined
   
