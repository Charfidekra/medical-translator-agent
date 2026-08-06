import io
import fitz  # PyMuPDF
import easyocr
import numpy as np
import streamlit as st
from main import translate_document
from PIL import Image

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


@st.cache_resource
def load_ocr_reader():
    """تحميل EasyOCR للغة الفرنسية والإنجليزية"""
    return easyocr.Reader(["fr", "en"], gpu=False)


def extract_page_text_with_ocr(img_pil, reader) -> str:
    """استخراج النصوص من الصورة عبر OCR مع التأكد من الاتجاه الصحيح"""
    img_np = np.array(img_pil)
    results = reader.readtext(img_np, detail=0)
    text = " ".join([t for t in results if t.strip()])
    
    # إذا كانت القراءة ضعيفة، نجرب تدوير الصورة 180 درجة لقراءتها في حال كانت مقلوبة
    if len(text) < 15:
        img_rotated = img_pil.rotate(180, expand=True)
        img_rotated_np = np.array(img_rotated)
        results_rotated = reader.readtext(img_rotated_np, detail=0)
        text_rotated = " ".join([t for t in results_rotated if t.strip()])
        if len(text_rotated) > len(text):
            return text_rotated, img_rotated
            
    return text, img_pil


def add_watermark(page, text="by dekra charfi"):
    """إضافة العلامة المائية"""
    rect = page.rect
    watermark_rect = fitz.Rect(
        rect.width * 0.1,
        rect.height * 0.45,
        rect.width * 0.9,
        rect.height * 0.55
    )
    page.insert_textbox(
        watermark_rect,
        text,
        fontsize=26,
        fontname="helv",
        color=(0.7, 0.7, 0.7),
        align=1,
        overlay=True
    )


def generate_side_by_side_pdf(uploaded_file, translator_func):
    reader = load_ocr_reader()

    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    new_doc = fitz.open()

    all_translated_texts = []

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]

        # تحويل الصفحة لصورة
        pix = orig_page.get_pixmap(dpi=120)
        img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

        # استخراج النص وتصحيح الاتجاه تلقائياً
        french_text, final_img_pil = extract_page_text_with_ocr(img_pil, reader)

        if french_text.strip():
            translated_text = translator_func(french_text)
        else:
            translated_text = "لم يتم العثور على نص واضح في هذه الصفحة."

        all_translated_texts.append(f"--- Page {page_num + 1} ---\n{translated_text}")

        # بناء النصف الأيمن (الترجمة)
        half_width = orig_page.rect.width
        page_height = orig_page.rect.height

        buffer = io.BytesIO()
        doc_temp = SimpleDocTemplate(
            buffer,
            pagesize=(half_width, page_height),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20,
        )

        styles = getSampleStyleSheet()
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
            spaceAfter=10,
        )

        story = [Paragraph(f"--- Translation Page {page_num + 1} ---", title_style)]

        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, custom_style))
                story.append(Spacer(1, 4))

        doc_temp.build(story)
        buffer.seek(0)

        # دمج النصفين أفقياً
        total_width = half_width * 2
        combo_page = new_doc.new_page(width=total_width, height=page_height)

        # رسم الصورة المصححة أيسر
        img_byte_arr = io.BytesIO()
        final_img_pil.save(img_byte_arr, format="PNG")
        combo_page.insert_image(
            fitz.Rect(0, 0, half_width, page_height),
            stream=img_byte_arr.getvalue()
        )

        # رسم النص المترجم أيمن
        translated_pdf_doc = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        combo_page.show_pdf_page(
            fitz.Rect(half_width, 0, total_width, page_height),
            translated_pdf_doc,
            0,
        )

        add_watermark(combo_page, "by dekra charfi")

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()
    orig_doc.close()

    output_buffer.seek(0)
    full_text_combined = "\n\n".join(all_translated_texts)
    return output_buffer.getvalue(), full_text_combined


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(page_title="Medical Translator Agent", page_icon="🩺", layout="wide")
st.title("🩺 Medical Translator Agent (Powered by Gemini)")

tab_text, tab_file = st.tabs(["📝 ترجمة نص مباشر", "📄 ترجمة ملف PDF"])

with tab_text:
    st.subheader("ترجمة النص الطبي مباشرة")
    user_input_text = st.text_area(
        label="أدخلي النص المراد ترجمته (فرنسي / عربي):",
        height=200,
        placeholder="أكتبي أو ألصقي النص هنا...",
    )

    if st.button("ترجمة النص", key="btn_translate_text"):
        if user_input_text.strip():
            with st.spinner("جاري ترجمة النص بواسطة Gemini..."):
                try:
                    result = translate_document(user_input_text)
                    st.success("✅ تمت الترجمة بنجاح!")
                    st.text_area(label="النص المترجم:", value=result, height=250)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الترجمة: {e}")
        else:
            st.warning("يرجى إدخال نص أولاً.")

with tab_file:
    st.subheader("رفع وترجمة ملف الـ PDF")
    uploaded_file = st.file_uploader(
        "قم برفع ملف الـ PDF الطبي", type=["pdf"]
    )

    if uploaded_file is not None:
        st.success("تم استلام الملف بنجاح!")

        if st.button("ترجمة الملف وإصدار النسخة المقسومة", key="btn_translate_file"):
            with st.spinner("جاري معالجة الصفحات والترجمة بوساطة Gemini..."):
                try:
                    final_pdf_bytes, combined_text = generate_side_by_side_pdf(
                        uploaded_file, translate_document
                    )
                    st.success("✅ تم معالجة المستند بنجاح!")

                    st.text_area(label="معاينة النص الإنجليزي المترجم:", value=combined_text, height=300)

                    st.download_button(
                        label="📥 تحميل الملف المترجم المقسوم (PDF)",
                        data=final_pdf_bytes,
                        file_name="side_by_side_translated.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء المعالجة: {e}")
