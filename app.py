
import io
import fitz  # PyMuPDF
import easyocr
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
import streamlit as st
from main import translate_document
from PIL import Image

# مكتبات بناء مستند منظم
from reportlab.lib.pagesizes import letter
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


def generate_aligned_translated_pdf(uploaded_file, translator_func) -> bytes:
    """
    إنشاء ملف PDF جديد يدمج صورة الصفحة الأصلية (مع كافة الصور والأشكال)
    وبجانبها/بعدها النص المترجم المنسق بدون أي تداخل في السطور.
    """
    reader = load_ocr_reader()
    
    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    new_doc = fitz.open()  # مستند مخرج جديد

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]
        
        # 1. استخراج صورة الصفحة الأصلية بكامل عناصرها وشكلها
        pix = orig_page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        # 2. قراءة النص من الصفحة وترجمته
        img_np = np.array(Image.open(io.BytesIO(img_bytes)))
        french_text = extract_page_text_with_ocr(img_np, reader)
        
        translated_text = ""
        if french_text.strip():
            translated_text = translator_func(french_text)
        else:
            translated_text = "No text detected on this page."

        # 3. إنشاء صفحة إنجليزية نظيفة ومنسقة
        buffer = io.BytesIO()
        doc_temp = SimpleDocTemplate(
            buffer,
            pagesize=(orig_page.rect.width, orig_page.rect.height),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )
        
        styles = getSampleStyleSheet()
        custom_style = ParagraphStyle(
            "DocStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=10,
        )
        
        story = []
        # إضافة عنوان رقم الصفحة
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            spaceAfter=12,
        )
        story.append(Paragraph(f"--- Translated Page {page_num + 1} ---", title_style))
        
        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, custom_style))
                story.append(Spacer(1, 6))

        doc_temp.build(story)
        buffer.seek(0)

        # 4. دمج الصفحة الأصلية (الصورة والتخطيط) تليها الصفحة المترجمة المنسقة
        # أ) إضافة الصفحة الأصلية بكامل صورها
        new_doc.insert_pdf(orig_doc, from_page=page_num, to_page=page_num)
        
        # ب) إضافة الصفحة المترجمة المنظمة
        translated_pdf_page = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        new_doc.insert_pdf(translated_pdf_page)

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
    page_title="Medical PDF Aligned Translator", page_icon="🩺", layout="wide"
)

st.title("🩺 Medical PDF Translator (منسق وبدون تداخل السطور)")

uploaded_file = st.file_uploader(
    "قم برفع ملف الـ PDF الطبي (سيتم إخراج ملف منظم يحتوي على الصفحة الأصلية وبجانبها الترجمة الإنجليزية)",
    type=["pdf"]
)

if uploaded_file is not None:
    st.success("تم استلام الملف بنجاح!")

    if st.button("ترجمة الملف وإنشاء نسخة منسقة"):
        with st.spinner("جاري معالجة الصفحة، كتابة الترجمة الإنجليزية وتنسيق المستند..."):
            try:
                final_pdf_bytes = generate_aligned_translated_pdf(
                    uploaded_file, translate_document
                )

                st.success("✅ تم إنشاء المستند المترجم بنجاح وبأعلى درجة تنسيق!")

                st.download_button(
                    label="📥 تحميل الملف المترجم المنظم (PDF)",
                    data=final_pdf_bytes,
                    file_name="aligned_translated_document.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة المستند: {e}")
