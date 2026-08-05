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


def add_watermark(page, text="by dekra charfi"):
    """إضافة علامة مائية بالاسم في مركز الصفحة"""
    rect = page.rect
    page.insert_text(
        fitz.Point(rect.width / 4, rect.height / 2),
        text,
        fontsize=28,
        fontname="helv",
        color=(0.7, 0.7, 0.7),
        rotate=45,
        overlay=True,
    )


def generate_side_by_side_pdf(uploaded_file, translator_func):
    """
    إنشاء صفحة أفقية مقسومة مع التعامل الآمن مع زوايا الدوران:
    - النصف الأيسر: صورة الصفحة الأصلية.
    - النصف الأيمن: النص المترجم المنسق.
    مع إضافة العلامة المائية by dekra charfi.
    """
    reader = load_ocr_reader()

    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    new_doc = fitz.open()

    all_translated_texts = []

    for page_num in range(len(orig_doc)):
        orig_page = orig_doc[page_num]

        # 1. الاستخراج الآمن للصورة دون المساس بزاوية الدوران الداخلية للـ PDF
        # نأخذ الـ Pixmap مع تعديل الزاوية للصفر في الخيارات إن وجدت
        pix = orig_page.get_pixmap(dpi=150)
        
        # تحويل الـ Pixmap إلى صورة PIL لمعالجتها بأمان
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # تصحيح الاتجاه إذا كانت زاوية الدوران معجلة في خصائص الصفحة
        rotation = orig_page.rotation
        if rotation in [90, 180, 270]:
            # تدوير الصورة بالاتجاه المعاكس لتعديلها
            img = img.rotate(-rotation, expand=True)

        # تحويل الصورة إلى Numpy Array لتمريرها لـ EasyOCR
        img_np = np.array(img)

        # 2. قراءة النص من الصفحة وترجمته
        french_text = extract_page_text_with_ocr(img_np, reader)

        translated_text = ""
        if french_text.strip():
            translated_text = translator_func(french_text)
        else:
            translated_text = "لا يوجد نص مستخرج في هذه الصفحة."

        all_translated_texts.append(
            f"--- Page {page_num + 1} ---\n{translated_text}"
        )

        # 3. إعداد أبعاد الصفحة
        # نعتمد أبعاد الصورة الفعلية بعد التعديل
        half_width = orig_page.rect.width
        page_height = orig_page.rect.height

        # إذا كانت الصفحة مدورة بـ 90 أو 270 درجة نعكس الأبعاد
        if rotation in [90, 270]:
            half_width, page_height = page_height, half_width

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

        story = [
            Paragraph(f"--- Translation Page {page_num + 1} ---", title_style)
        ]

        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, custom_style))
                story.append(Spacer(1, 4))

        doc_temp.build(story)
        buffer.seek(0)

        # 4. دمج الجانبين في صفحة أفقية واحدة (Landscape)
        total_width = half_width * 2
        combo_page = new_doc.new_page(width=total_width, height=page_height)

        # أ) رسم الصورة المصححة للصفحة الأصلية في النصف الأيسر
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        combo_page.insert_image(
            fitz.Rect(0, 0, half_width, page_height),
            stream=img_byte_arr.getvalue()
        )

        # ب) رسم النص المترجم المنسق في النصف الأيمن
        translated_pdf_doc = fitz.open(
            stream=buffer.getvalue(), filetype="pdf"
        )
        combo_page.show_pdf_page(
            fitz.Rect(half_width, 0, total_width, page_height),
            translated_pdf_doc,
            0,
        )

        # ج) إضافة العلامة المائية "by dekra charfi"
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
st.set_page_config(
    page_title="Medical Translator Agent", page_icon="🩺", layout="wide"
)

st.title("🩺 Medical Translator Agent")

# تقسيم الواجهة إلى تبويبين رئيسيين
tab_text, tab_file = st.tabs(["📝 ترجمة نص مباشر", "📄 ترجمة ملف PDF"])

# ====================================================
# الخانة الأولى: ترجمة نص مباشر
# ====================================================
with tab_text:
    st.subheader("ترجمة النص الطبي مباشرة")
    user_input_text = st.text_area(
        label="أدخلي النص المراد ترجمته (فرنسي / إنجليزي):",
        height=200,
        placeholder="أكتبي أو ألصقي النص هنا...",
    )

    if st.button("ترجمة النص", key="btn_translate_text"):
        if user_input_text.strip():
            with st.spinner("جاري ترجمة النص بواسطة الطاقم الطبي الذكي..."):
                try:
                    result = translate_document(user_input_text)
                    st.success("✅ تمت الترجمة بنجاح!")
                    st.subheader("النتيجة:")
                    st.text_area(
                        label="النص المترجم:",
                        value=result,
                        height=250,
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء ترجمة النص: {e}")
        else:
            st.warning("يرجى إدخال نص أولاً قبل الضغط على زر الترجمة.")

# ====================================================
# الخانة الثانية: ترجمة ملف PDF
# ====================================================
with tab_file:
    st.subheader("رفع وترجمة ملف الـ PDF")
    uploaded_file = st.file_uploader(
        "قم برفع ملف الـ PDF الطبي (سيتم تصحيح اتجاه الصفحات المقلوبة وتقسيم الصفحات مع إضافة العلامة المائية)",
        type=["pdf"],
    )

    if uploaded_file is not None:
        st.success("تم استلام الملف بنجاح!")

        if st.button("ترجمة الملف وإصدار النسخة المقسومة", key="btn_translate_file"):
            with st.spinner(
                "جاري تصحيح الاتجاه، الترجمة، وإضافة العلامة المائية by dekra charfi..."
            ):
                try:
                    final_pdf_bytes, combined_text = generate_side_by_side_pdf(
                        uploaded_file, translate_document
                    )

                    st.success("✅ تم معالجة المستند بنجاح!")

                    # معاينة النص المترجم
                    st.subheader("📝 النص المترجم المستخرج من الملف:")
                    st.text_area(
                        label="معاينة النص الإنجليزي المترجم:",
                        value=combined_text,
                        height=300,
                    )

                    # زر تحميل PDF المقسوم
                    st.download_button(
                        label="📥 تحميل الملف المترجم المقسوم (PDF)",
                        data=final_pdf_bytes,
                        file_name="side_by_side_translated.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء معالجة المستند: {e}")
