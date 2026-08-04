import streamlit as st
import pdfplumber
import pypdfium2 as pdfium
from main import translate_document


def extract_text_from_pdf(uploaded_file) -> str:
    """استخراج النص من ملف الـ PDF بأكثر من طريقة مفضلة"""
    full_text = ""

    # المحاولة الأولى: عبر pdfplumber
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

    # المحاولة الثانية: عبر pypdfium2 في حال فشل الأولى
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

# إتاحة الخيارين للمستخدم
option = st.radio(
    "اختر طريقة إدخال النص الطبي:",
    ("رفع ملف (PDF / TXT)", "كتابة / نسخ النص مباشرة"),
    horizontal=True
)

source_text = ""

if option == "رفع ملف (PDF / TXT)":
    uploaded_file = st.file_uploader(
        "قم برفع ملف طبّي", type=["pdf", "txt"]
    )
    if uploaded_file is not None:
        filename = uploaded_file.name.lower()
        if filename.endswith(".pdf"):
            extracted = extract_text_from_pdf(uploaded_file)
            if extracted.strip():
                source_text = extracted
                st.success(f"تم استخراج النص بنجاح! ({len(source_text.split())} كلمة)")
            else:
                st.error(
                    "❌ تعذر استخراج النص لأن ملف الـ PDF عبارة عن صور (Scanned PDF). "
                    "يمكنك نسخ النص من الملف ولصقه عبر خيار 'كتابة / نسخ النص مباشرة'."
                )
        else:
            source_text = uploaded_file.getvalue().decode("utf-8")
            st.success("تم تحميل الملف النصي بنجاح!")

else:
    source_text = st.text_area(
        "أدخل النص الطبي بالفرنسية هنا:",
        height=250,
        placeholder="L'insuffisance rénale aiguë est définie par..."
    )

# ----------------------------------------------------
# زر الترجمة والعرض
# ----------------------------------------------------
if source_text.strip():
    with st.expander("عرض النص الذي سيتم ترجمته"):
        st.write(source_text)

    if st.button("ترجمة النص"):
        with st.spinner("جاري الترجمة والتدقيق عبر CrewAI..."):
            try:
                translated_result = translate_document(source_text)
                st.subheader("الترجمة النهائية:")
                st.write(translated_result)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الترجمة: {e}")
