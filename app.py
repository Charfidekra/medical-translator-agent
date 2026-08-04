import base64
import io
import os
import pdfplumber
import pypdfium2 as pdfium
import streamlit as st
from main import translate_document
from openai import OpenAI
from PIL import Image

def ocr_image_with_groq(image: Image.Image, groq_key: str) -> str:
    """استخراج النص من الصورة باستخدام نماذج Vision المعتمدة من Groq"""
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1", api_key=groq_key
    )

    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # قائمة بأحدث أسماء نماذج الرؤية المتاحة على Groq
    vision_models = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-11b-vision-instruct",
    ]

    for model_name in vision_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image exactly as it is, maintaining sentence order. Do not translate, just extract the exact French text.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception:
            continue

    raise RuntimeError("تعذر الوصول إلى نموذج رؤية نشط في Groq API.")


def extract_text_from_pdf(uploaded_file, groq_key: str) -> str:
    """استخراج النص بالطريقة العادية، وإن تعذر يتم اللجوء للـ Vision OCR تلقائياً"""
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

    # المحاولة الثالثة: Groq Vision OCR (للملفات المصورة)
    if not full_text.strip():
        st.info("🔄 الملف عبارة عن صور/سكانر، جاري استخراج النص بواسطة الذكاء الاصطناعي...")
        try:
            uploaded_file.seek(0)
            pdf = pdfium.PdfDocument(uploaded_file)
            ocr_texts = []
            
            for page in pdf:
                # تحويل كل صفحة إلى صورة
                image = page.render(scale=2).to_pil()
                extracted_page_text = ocr_image_with_groq(image, groq_key)
                if extracted_page_text.strip():
                    ocr_texts.append(extracted_page_text)
            
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

groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

option = st.radio(
    "اختر طريقة إدخال النص الطبي:",
    ("رفع ملف (PDF / TXT)", "كتابة / نسخ النص مباشرة"),
    horizontal=True,
)

source_text = ""

if option == "رفع ملف (PDF / TXT)":
    uploaded_file = st.file_uploader(
        "قم برفع ملف طبّي (حتى لو كان صور/سكانر)", type=["pdf", "txt"]
    )
    if uploaded_file is not None:
        filename = uploaded_file.name.lower()
        if filename.endswith(".pdf"):
            source_text = extract_text_from_pdf(uploaded_file, groq_key)
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
    with st.expander("عرض النص الاستخراجي الأصلي"):
        st.write(source_text)

    if st.button("ترجمة النص"):
        with st.spinner("جاري الترجمة والتدقيق عبر CrewAI..."):
            try:
                translated_result = translate_document(source_text)
                st.subheader("الترجمة النهائية:")
                st.write(translated_result)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الترجمة: {e}")
