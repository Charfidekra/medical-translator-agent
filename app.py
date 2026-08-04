import easyocr
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
import streamlit as st
from main import translate_document
from PIL import Image

# تحميل قارئ EasyOCR وتخزينه في الـ Cache لضمان السرعة وتجنب إعادة التحميل مع كل إدخال
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['fr', 'en'], gpu=False)

def extract_text_from_pdf(uploaded_file) -> str:
    """استخراج النص بالطريقة النصية العادية، وإن تعذر يتم استخدام EasyOCR تلقائياً"""
    full_text = ""

    # المحاولة الأولى: pdfplumber
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            pages_text = [
                p.extract_text(layout=True)
                for p in pdf.pages
                if p.extract_text(layout=True)
            ]
            full_text = "\n\n".join(pages_text)
    except Exception:
        full_text = ""

    # المحاولة الثانية: pypdfium2
    if not full_text.strip():
        try:
            uploaded_file.seek(0)
            pdf = pdfium.PdfDocument(uploaded_file)
            pages_text = [
                p.get_textpage().get_text_range()
                for p in pdf
                if p.get_textpage().get_text_range().strip()
            ]
            full_text = "\n\n".join(pages_text)
        except Exception:
            full_text = ""

    # المحاولة الثالثة: EasyOCR (في حال كان الملف عبارة عن صور/سكانر)
    if not full_text.strip():
        st.info("🔄 الملف عبارة عن صور/سكانر، جاري استخراج النص بواسطة محرك OCR...")
        try:
            reader = load_ocr_reader()
            uploaded_file.seek(0)
            pdf = pdfium.PdfDocument(uploaded_file)
            ocr_texts = []

            for page in pdf:
                # تحويل صفحة الـ PDF إلى صورة
                image = page.render(scale=2).to_pil()
                img_np = np.array(image)
                
                # استخراج النصوص الفرنسية والإنجليزية من الصورة
                results = reader.readtext(img_np, detail=0)
                page_extracted = " ".join(results)
                if page_extracted.strip():
                    ocr_texts.append(page_extracted)

            full_text = "\n\n".join(ocr_texts)
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الصور: {e}")

    return full_text


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(
    page_title="Medical Translator",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 Medical French-to-English Translator Agent")

option = st.radio(
    "اختر طريقة إدخال النص الطبي:",
    ("رفع ملف (PDF / TXT)", "كتابة / نسخ النص مباشرة"),
    horizontal=True,
)

source_text = ""

if option == "رفع ملف (PDF / TXT)":
    uploaded_file = st.file_uploader(
        "قم برفع ملف طبّي (PDF نصي أو مصوّر / TXT)", type=["pdf", "txt"]
    )
    if uploaded_file is not None:
        filename = uploaded_file.name.lower()
        if filename.endswith(".pdf"):
            source_text = extract_text_from_pdf(uploaded_file)
            if source_text.strip():
                st.success(f"تم استخراج النص بنجاح! ({len(source_text.split())} كلمة)")
            else:
                st.error("❌ تعذر استخراج النص من الملف.")
        else:
            source_text = uploaded_file.getvalue().decode("utf-8")
            st.success("تم تحميل الملف النصي بنجاح!")

else:
    source_text = st.text_area(
        "أدخل النص الطبي بالفرنسية هنا:",
        height=250,
        placeholder="L'insuffisance rénale aiguë est définie par...",
    )

# ----------------------------------------------------
# زر الترجمة والعرض
# ----------------------------------------------------
if source_text.strip():
    with st.expander("عرض النص المستخرج الأصلي"):
        st.write(source_text)

    if st.button("ترجمة النص"):
        with st.spinner("جاري الترجمة والتدقيق عبر CrewAI..."):
            try:
                translated_result = translate_document(source_text)
                st.subheader("الترجمة النهائية:")
                st.write(translated_result)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الترجمة: {e}")
