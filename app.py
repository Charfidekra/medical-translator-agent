import io
import fitz  # PyMuPDF
import easyocr
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
import streamlit as st
from main import translate_document
from PIL import Image


@st.cache_resource
def load_ocr_reader():
    """تحميل EasyOCR وتخزينه في الذاكرة"""
    return easyocr.Reader(["fr", "en"], gpu=False)


def replace_text_in_pdf_layout(uploaded_file, groq_translator_func) -> bytes:
    """
    تقوم هذه الدالة بفتح الـ PDF الأصلي، تحديد أماكن النصوص الفرنسية،
    مسحها (White-out) مع ترك الصور في مكانها، ثم كتابة الترجمة فوق الصفحة الأصلية.
    """
    reader = load_ocr_reader()
    
    # فتح المستند الأصلي باستخدام PyMuPDF
    uploaded_file.seek(0)
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. تحويل الصفحة إلى صورة لاستخراج النصوص والـ Bounding Boxes
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img_np = np.array(img)

        # 2. قراءة النصوص مع مواضعها الجغرافية بالصفحة (bboxes)
        ocr_results = reader.readtext(img_np)
        
        if not ocr_results:
            continue

        # تجميع كامل النص الفرنسي الخاص بالصفحة لترجمته
        page_french_text = " ".join([res[1] for res in ocr_results if res[1].strip()])
        
        if not page_french_text.strip():
            continue

        # 3. ترجمة النص الفرنسي الكامل للصفحة إلى الإنجليزية
        translated_page_text = groq_translator_func(page_french_text)

        # 4. مسح الكلمات الفرنسية القديمة من الصفحة الأصلية (مع ترك الصور دون لمس)
        # أبعاد الصفحة في fitz تختلف قليلاً عن أبعاد الصورة
        rect_scale_x = page.rect.width / img_np.shape[1]
        rect_scale_y = page.rect.height / img_np.shape[0]

        for bbox, text, prob in ocr_results:
            # حساب مستطيل النص الأصلي
            (tl, tr, br, bl) = bbox
            x0, y0 = tl[0] * rect_scale_x, tl[1] * rect_scale_y
            x1, y1 = br[0] * rect_scale_x, br[1] * rect_scale_y
            
            rect = fitz.Rect(x0, y0, x1, y1)
            # تغطية النص الفرنسي القديم بمستطيل أبيض لمسحه
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        # 5. كتابة النص المترجم في أعلى منطقة النص مع الحفاظ على أبعاد باقي العناصر والصور
        # نأخذ أول منطقة بدأ فيها النص بالصفحة
        first_bbox = ocr_results[0][0]
        start_x = first_bbox[0][0] * rect_scale_x
        start_y = first_bbox[0][1] * rect_scale_y
        
        target_rect = fitz.Rect(
            start_x, 
            start_y, 
            page.rect.width - 20, 
            page.rect.height - 20
        )

        # إدراج النص المترجم بداخل الصفحة الأصلية
        page.insert_textbox(
            target_rect,
            translated_page_text,
            fontsize=9,
            fontname="helv",
            color=(0, 0, 0)
        )

    # حفظ المستند الأصلي المعدل بنفس الترتيب والصور
    output_buffer = io.BytesIO()
    doc.save(output_buffer)
    doc.close()
    output_buffer.seek(0)
    return output_buffer.getvalue()


# ----------------------------------------------------
# واجهة Streamlit
# ----------------------------------------------------
st.set_page_config(
    page_title="Medical PDF Layout Translator", page_icon="🩺", layout="wide"
)

st.title("🩺 Medical PDF Translator (مع الحفاظ على الأشكال والصور)")

uploaded_file = st.file_uploader(
    "قم برفع ملف الـ PDF الأصلي (سيتم استبدال النص بالترجمة مع الإبقاء على مكان الصور)",
    type=["pdf"]
)

if uploaded_file is not None:
    st.success("تم استلام الملف بنجاح! جاهز للمعالجة والاستبدال المباشر.")

    if st.button("ترجمة الملف وإصدار نسخة مستبدلة بنفس التنسيق"):
        with st.spinner("جاري مسح النصوص الفرنسية، كتابة الترجمة الإنجليزية وتصميم المستند الأصلي..."):
            try:
                # تشغيل معالجة الملف واستبدال النصوص داخل التخطيط الأصلي
                translated_pdf_bytes = replace_text_in_pdf_layout(
                    uploaded_file, translate_document
                )

                st.success("✅ تم إكمال العملية بنجاح وتحديث المستند الأصلي!")

                # تقديم زر التحميل للملف التفاعلي المترجم
                st.download_button(
                    label="📥 تحميل الملف الأصلي المترجم (مع الصور والتخطيط)",
                    data=translated_pdf_bytes,
                    file_name="translated_layout_document.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة المستند: {e}")
