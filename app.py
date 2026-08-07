import io
import gc
import fitz  # PyMuPDF
import streamlit as st
from PIL import Image
from main import translate_document

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def extract_lightweight_text(page) -> tuple[str, Image.Image]:
    """استخراج نص سريع خفيف جداً على الذاكرة والـ CPU"""
    direct_text = page.get_text("text").strip()
    pix = page.get_pixmap(dpi=120)  # تقليل الـ DPI قليلاً لتوفير ذاكرة الهاتف
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))
    return direct_text, img_pil


def generate_side_by_side_pdf(uploaded_file, translator_func):
    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    new_doc = fitz.open()

    all_translated_texts = []

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]

        extracted_text, final_img_pil = extract_lightweight_text(orig_page)

        if extracted_text.strip():
            translated_text = translator_func(extracted_text)
        else:
            translated_text = "No selectable text found on this page (scanned page)."

        all_translated_texts.append(f"--- Page {page_num + 1} ---\n{translated_text}")

        half_width = orig_page.rect.width
        page_height = orig_page.rect.height

        buffer = io.BytesIO()
        doc_temp = SimpleDocTemplate(
            buffer,
            pagesize=(half_width, page_height),
            rightMargin=20,
            leftMargin=20,
            topMargin=25,
            bottomMargin=25,
        )

        styles = getSampleStyleSheet()
        
        watermark_style = ParagraphStyle(
            "WatermarkStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor="#888888",
            alignment=1,
            spaceAfter=6,
        )

        custom_style = ParagraphStyle(
            "SideBySideStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            spaceAfter=8,
        )

        title_style = ParagraphStyle(
            "SideTitleStyle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            spaceAfter=6,
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
                story.append(Paragraph(formatted, custom_style))
                story.append(Spacer(1, 4))

        story.append(Spacer(1, 10))
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
            translated_pdf_doc,
            0,
        )
        
        # تفريغ الذاكرة
        gc.collect()

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()
    orig_doc.close()

    output_buffer.seek(0)
    full_text_combined = "\n\n".join(all_translated_texts)
    return output_buffer.getvalue(), full_text_combined


# ----------------------------------------------------
# واجهة التطبيق
# ----------------------------------------------------
st.set_page_config(page_title="MEDICAL TRANSLATOR AGENT", page_icon="🩺", layout="wide")
st.title("🩺 MEDICAL TRANSLATOR AGENT")
st.caption("Advanced Medical & Population Genetics Translation Engine | **BY DEKRA CHARFI**")

tab_text, tab_file = st.tabs(["📝 ترجمة نص مباشر", "📄 ترجمة ملف PDF (مع العلامة المائية)"])

with tab_text:
    st.subheader("ترجمة النص الطبي المباشر وتصحيح المعادلات")
    user_input_text = st.text_area(
        label="أدخلي النص المراد ترجمته (فرنسي / عربي):",
        height=200,
        placeholder="أكتبي أو ألصقي النص هنا...",
    )

    if st.button("ترجمة النص", key="btn_translate_text"):
        if user_input_text.strip():
            with st.spinner("جاري الترجمة والتصحيح الأكاديمي بواسطة MEDICAL TRANSLATOR AGENT..."):
                result = translate_document(user_input_text)
                if result.startswith("Error") or result.startswith("Translation Service Error"):
                    st.error(result)
                else:
                    st.success("✅ تمت الترجمة بنجاح!")
                    st.text_area(label="النص المترجم والمصحح:", value=result, height=250)
        else:
            st.warning("يرجى إدخال نص أولاً.")

with tab_file:
    st.subheader("رفع وترجمة ملف الـ PDF")
    uploaded_file = st.file_uploader(
        "قم برفع ملف الـ PDF الطبي/الجيني", type=["pdf"]
    )

    if uploaded_file is not None:
        st.success("تم استلام الملف بنجاح!")

        if st.button("ترجمة المستند وتوليد PDF المقسوم", key="btn_translate_file"):
            with st.spinner("جاري الترجمة وتوليد الـ PDF..."):
                try:
                    final_pdf_bytes, combined_text = generate_side_by_side_pdf(
                        uploaded_file, translate_document
                    )
                    st.success("✅ تم معالجة المستند بنجاح!")

                    st.text_area(label="معاينة النص الإنجليزي المترجم والمصحح:", value=combined_text, height=300)

                    st.download_button(
                        label="📥 تحميل الملف المترجم (PDF) - BY DEKRA CHARFI",
                        data=final_pdf_bytes,
                        file_name="translated_genetics_BY_DEKRA_CHARFI.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء المعالجة: {e}")
   
