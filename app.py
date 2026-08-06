import io
import fitz  # PyMuPDF
import easyocr
import numpy as np
import streamlit as st
from main import translate_document
from PIL import Image

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import letter


@st.cache_resource
def load_ocr_reader():
    """تحميل مكتبة EasyOCR لقراءة الفرنسية والإنجليزية"""
    return easyocr.Reader(["fr", "en"], gpu=False)


def extract_page_text_with_ocr(img_pil, reader) -> str:
    """استخراج النص من الصورة بواسطة OCR"""
    img_np = np.array(img_pil)
    results = reader.readtext(img_np, detail=0)
    text = " ".join([t for t in results if t.strip()])
    return text


def create_simple_pdf(translated_text: str) -> bytes:
    """إنشاء ملف PDF بسيط يحتوي على النص المترجم كاملاً"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(
        "TranslatedStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=10,
    )
    
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        spaceAfter=15,
    )

    story = [Paragraph("Translated Medical Document", title_style), Spacer(1, 10)]

    for para in translated_text.split("\n\n"):
        if para.strip():
            formatted = para.strip().replace("\n", "<br/>")
            story.append(Paragraph(formatted, custom_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def process_pdf_translation(uploaded_file, translator_func):
    """استخراج النصوص من صفحات الـ PDF وترجمتها مباشرة"""
    reader = load_ocr_reader()

    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

    translated_pages = []

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]

        # استخراج صورة الصفحة
        pix = orig_page.get_pixmap(dpi=120)
        img_pil = Image.open(io.BytesIO(pix.tobytes("png")))
        
        # قراءة النص بالـ OCR
        extracted_text = extract_page_text_with_ocr(img_pil, reader)

        # الترجمة
        if extracted_text.strip():
            translated_text = translator_func(extracted_text)
        else:
            translated_text = "لم يتم العثور على نص واضح في هذه الصفحة."

        page_header = f"=== Page {page_num + 1} ==="
        translated_pages.append(f"{page_header}\n\n{translated_text}")

    orig_doc.close()
    full_translated_content = "\n\n".join(translated_pages)
    return full_translated_content


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(page_title="Medical Translator Agent", page_icon="🩺", layout="wide")
st.title("🩺 Medical Translator Agent (Powered by Groq)")

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
            with st.spinner("جاري ترجمة النص بواسطة Groq..."):
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

        if st.button("ترجمة المستند واستخراج النص", key="btn_translate_file"):
            with st.spinner("جاري قراءة الصفحة وترجمتها بـ Groq..."):
                try:
                    translated_result = process_pdf_translation(
                        uploaded_file, translate_document
                    )
                    st.success("✅ تم استخراج الترجمة بنجاح!")

                    st.text_area(
                        label="النص الطبي المترجم كاملاً:", 
                        value=translated_result, 
                        height=400
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 تحميل الترجمة كملف نصي (.txt)",
                            data=translated_result,
                            file_name="translated_document.txt",
                            mime="text/plain",
                        )
                    with col2:
                        pdf_data = create_simple_pdf(translated_result)
                        st.download_button(
                            label="📥 تحميل الترجمة كملف PDF",
                            data=pdf_data,
                            file_name="translated_document.pdf",
                            mime="application/pdf",
                        )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء المعالجة: {e}")
