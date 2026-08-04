import streamlit as st
import pypdfium2 as pdfium
from main import translate_document


def extract_text_from_upload(uploaded_file) -> str:
    """استخراج النص سواء كان الملف .txt أو .pdf"""
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        # قراءة ملف الـ PDF باستخدام pypdfium2
        pdf = pdfium.PdfDocument(uploaded_file)
        extracted_text = []

        for page in pdf:
            textpage = page.get_textpage()
            page_text = textpage.get_text_range()
            if page_text and page_text.strip():
                extracted_text.append(page_text)

        full_text = "\n\n".join(extracted_text)

        if not full_text.strip():
            raise ValueError(
                "لم يتم العثور على نص قابل للاستخراج داخل ملف الـ PDF."
            )

        return full_text
    else:
        # للملفات النصية العادية .txt
        return uploaded_file.getvalue().decode("utf-8")


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(
    page_title="Medical Translator",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 Medical French-to-English Translator Agent")

uploaded_file = st.file_uploader(
    "قم برفع ملف طبّي (PDF أو TXT)", type=["pdf", "txt"]
)

if uploaded_file is not None:
    try:
        source_text = extract_text_from_upload(uploaded_file)
        st.success(
            f"تم استخراج النص بنجاح! ({len(source_text.split())} كلمة)"
        )

        with st.expander("عرض النص المستخرج من الملف"):
            st.text_area("النص الأصلي", source_text, height=200)

        if st.button("ترجمة المستند"):
            with st.spinner("جاري الترجمة والتدقيق عبر CrewAI..."):
                translated_result = translate_document(source_text)
                st.subheader("الترجمة النهائية:")
                st.write(translated_result)

    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
