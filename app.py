import io
import fitz  # PyMuPDF
import easyocr
import numpy as np
import streamlit as st
from main import translate_document
from PIL import Image

# مكتبات تنسيق النص المترجم
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


@st.cache_resource
def load_ocr_reader():
    """تحميل EasyOCR وتخزينه في الذاكرة لضمان السرعة"""
    return easyocr.Reader(["fr", "en"], gpu=False)


def extract_page_text_with_ocr(page_img_np, reader) -> str:
    """استخراج النصوص من صورة الصفحة عبر EasyOCR"""
    results = reader.readtext(page_img_np, detail=0)
    return " ".join([t for t in results if t.strip()])


def generate_side_by_side_pdf(uploaded_file, translator_func) -> bytes:
    """
    تقوم هذه الدالة بإنشاء صفحة أفقية (Landscape) مقسومة إلى نصفين:
    - النصف الأيسر: صورة الصفحة الأصلية بكامل صورها وجداولها.
    - النصف الأيمن: النص المترجم منسق ومقابل لها تماماً.
    """
    reader = load_ocr_reader()

    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    new_doc = fitz.open()

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]

        # 1. استخراج صورة الصفحة الأصلية بكامل صورها وأشكالها
        pix = orig_page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")

        # 2. قراءة النص من الصفحة وترجمته
        img_np = np.array(Image.open(io.BytesIO(img_bytes)))
        french_text = extract_page_text_with_ocr(img_np, reader)

        translated_text = ""
        if french_text.strip():
            translated_text = translator_func(french_text)
        else:
            translated_text = "لا يوجد نص مستخرج في هذه الصفحة."

        # 3. إنشاء مستند وقتي للنصف المترجم الأيمن
        # أبعاد النصف الأيمن تكون مساوية لأبعاد الصفحة الأصلية
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

        # 4. دمج الجانبين في صفحة واحدة أفقية (Landscape)
        # العرض الكلي للصفحة الجديدة = عرض الصفحة الأصلية × 2
        total_width = half_width * 2
        combo_page = new_doc.new_page(width=total_width, height=page_height)

        # أ) رسم الصفحة الأصلية بالصور والأشكال في النصف الأيسر
        combo_page.show_pdf_page(
            fitz.Rect(0, 0, half_width, page_height),
            orig_doc,
            page_num
        )

        # ب) رسم النص المترجم المنسق في النصف الأيمن
        translated_pdf_doc = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        combo_page.show_pdf_page(
            fitz.Rect(half_width, 0, total_width, page_height),
            translated_pdf_doc,
            0
        )

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()
    orig_doc.close()

    output_buffer.seek(0)
    return output_buffer.getvalue()


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(
    page_title="Medical Split PDF Translator", page_icon="🩺", layout="wide"
)

st.title("🩺 Medical PDF Translator (صفحة أفقية مقسومة: أصل + ترجمة)")

uploaded_file = st.file_uploader(
    "قم برفع ملف الـ PDF الطبي",
    type=["pdf"]
)

if uploaded_file is not None:
    st.success("تم استلام الملف بنجاح!")

    if st.button("ترجمة الملف وإنشاء المستند المقسوم (Side-by-Side)"):
        with st.spinner("جاري الترجمة وإعادة تقسيم الصفحة بالعرض..."):
            try:
                final_pdf_bytes = generate_side_by_side_pdf(
                    uploaded_file, translate_document
                )

                st.success("✅ تم دمج الأصل والترجمة في صفحة واحدة بالعرض بنجاح!")

                st.download_button(
                    label="📥 تحميل الملف المترجم المقسوم (PDF)",
                    data=final_pdf_bytes,
                    file_name="side_by_side_translated.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة المستند: {e}")
