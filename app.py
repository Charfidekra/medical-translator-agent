import io
import gc
import base64
import os
from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from litellm import completion
from pptx import Presentation

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from main import translate_document  # ملف main.py يحتوي على دالة الترجمة


# ----------------------------------------------------
# 1. واجهة الأذكار والتسبيحات أثناء المعالجة
# ----------------------------------------------------
AZKAR_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  body {
    background-color: #0e1117;
    color: #ffffff;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 15px;
    margin: 0;
  }
  .card {
    background: #1e2530;
    border: 1px solid #313d4f;
    border-radius: 12px;
    padding: 20px;
    width: 90%;
    max-width: 450px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
  }
  .title {
    color: #00e676;
    font-size: 16px;
    margin-bottom: 12px;
    font-weight: bold;
  }
  .zikr {
    font-size: 20px;
    color: #ffffff;
    min-height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1.5;
    margin-bottom: 10px;
  }
  .sub {
    font-size: 12px;
    color: #8b9bb4;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="title">✨ جاري معالجة المستند... استغل الوقت بالذكر</div>
    <div class="zikr" id="zikr-box">سُبْحَانَ اللَّهِ وَبِحَمْدِهِ ، سُبْحَانَ اللَّهِ الْعَظِيمِ</div>
    <div class="sub">يتغيّر الذكر تلقائياً كل بضع ثوانٍ</div>
  </div>

<script>
  const azkar = [
    "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ ، سُبْحَانَ اللَّهِ الْعَظِيمِ",
    "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ",
    "لا حَوْلَ وَلا قُوَّةَ إِلاَّ بِاللَّهِ الْعَلِيِّ الْعَظِيمِ",
    "اللَّهُمَّ صَلِّ وَسَلِّمْ وَبَارِكْ عَلَى نَبِيِّنَا مُحَمَّدٍ",
    "لا إِلَهَ إِلاَّ أَنْتَ سُبْحَانَكَ إِنِّي كُنْتُ مِنَ الظَّالِمِينَ",
    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "سُبْحَانَ اللَّهِ ، وَالْحَمْدُ لِلَّهِ ، وَلا إِلَهَ إِلاَّ اللَّهُ ، وَاللَّهُ أَكْبَرُ"
  ];
  let idx = 0;
  setInterval(() => {
    idx = (idx + 1) % azkar.length;
    document.getElementById("zikr-box").innerText = azkar[idx];
  }, 4000);
</script>
</body>
</html>
"""


# ----------------------------------------------------
# 2. الترجمة الاحتياطية باستخدام النموذج المستقر Llama 3.3
# ----------------------------------------------------
def translate_scanned_image(img_pil: Image.Image) -> str:
    """استخدام النموذج المستقر Llama 3.3 من Groq لتجنب أخطاء Deprecated Models"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY environment variable is not set."

    system_prompt = (
        "You are an elite Clinical Genetics Professor and Expert Medical Translator.\n"
        "Translate and summarize the medical concepts present in this page into highly accurate academic English.\n"
        "STRICT RULES:\n"
        "1. Preserve all clinical and genetic terms (Hardy-Weinberg genotypes AA, Aa, aa).\n"
        "2. Do not omit any medical content.\n"
        "3. Output ONLY the translated academic English text without preamble."
    )

    try:
        # استخدام النموذج الرسمي المعتمد والمستقر لـ Groq
        response = completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please translate and process this medical page content."}
            ],
            temperature=0.1,
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Translation Error: {str(e)}"


# ----------------------------------------------------
# 3. معالجة وتفريك الصفحات
# ----------------------------------------------------
def extract_pages_from_file(uploaded_file):
    file_ext = uploaded_file.name.split(".")[-1].lower()
    pages_data = []

    if file_ext == "pdf":
        uploaded_file.seek(0)
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            pix = page.get_pixmap(dpi=110)
            img_pil = Image.open(io.BytesIO(pix.tobytes("png")))
            w, h = page.rect.width, page.rect.height
            pages_data.append((page_num, text, img_pil, w, h))
        doc.close()

    elif file_ext in ["pptx", "ppt"]:
        uploaded_file.seek(0)
        prs = Presentation(uploaded_file)
        w, h = 720, 540 
        for idx, slide in enumerate(prs.slides):
            text_runs = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text_runs.append(paragraph.text)
            full_text = "\n".join(text_runs).strip()
            img_pil = Image.new('RGB', (int(w), int(h)), color=(245, 247, 250))
            pages_data.append((idx, full_text, img_pil, w, h))

    return pages_data


def process_single_page_data(args):
    page_num, text, img_pil, width, height, translator_func = args

    if text and len(text) > 20:
        translated_text = translator_func(text)
    else:
        translated_text = translate_scanned_image(img_pil)

    gc.collect()
    return page_num, translated_text, img_pil, width, height


def generate_side_by_side_pdf_safe(uploaded_file, translator_func):
    pages_raw = extract_pages_from_file(uploaded_file)
    total_pages = len(pages_raw)

    tasks = [
        (p_num, text, img, w, h, translator_func)
        for p_num, text, img, w, h in pages_raw
    ]

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("🚀 جاري معالجة المستند وقراءة الصفحات...")

    results = [None] * total_pages

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_single_page_data, task) for task in tasks]
        completed = 0
        for future in futures:
            p_num, trans_text, img_pil, width, height = future.result()
            results[p_num] = (trans_text, img_pil, width, height)
            completed += 1
            progress_bar.progress(completed / total_pages)
            status_text.text(f"⚡ تم إكمال ترجمة {completed} من أصل {total_pages} صفحات/شرائح...")

    status_text.text("🎨 جاري إضفاء العلامة المائية وتجميع ملف الـ PDF النهائي...")

    new_doc = fitz.open()
    all_translated_texts = []

    for page_num, (translated_text, final_img_pil, half_width, page_height) in enumerate(results):
        all_translated_texts.append(f"--- Page/Slide {page_num + 1} ---\n{translated_text}")

        buffer = io.BytesIO()
        doc_temp = SimpleDocTemplate(
            buffer,
            pagesize=(half_width, page_height),
            rightMargin=18,
            leftMargin=18,
            topMargin=20,
            bottomMargin=20,
        )

        styles = getSampleStyleSheet()
        
        # العلامة المائية المطلوبة: BY CHARFI DEKRA
        watermark_style = ParagraphStyle(
            "WatermarkStyle", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=8, textColor="#ff4b4b", alignment=1, spaceAfter=4
        )
        title_style = ParagraphStyle(
            "SideTitleStyle", parent=styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=10, spaceAfter=6
        )

        char_count = len(translated_text)
        f_size = 7 if char_count > 1500 else (8 if char_count > 800 else 9)
        leading = f_size + 3

        dynamic_style = ParagraphStyle(
            "DynamicStyle", parent=styles["Normal"],
            fontName="Helvetica", fontSize=f_size, leading=leading, spaceAfter=4
        )

        story = [
            Paragraph("— TRANSLATED BY MEDICAL TRANSLATOR AGENT —", watermark_style),
            Paragraph("BY CHARFI DEKRA", watermark_style),
            Spacer(1, 4),
            Paragraph(f"--- Translation Page/Slide {page_num + 1} ---", title_style)
        ]

        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, dynamic_style))
                story.append(Spacer(1, 2))

        # إدراج العلامة المائية في التذييل السفلي
        story.append(Spacer(1, 6))
        story.append(Paragraph("BY CHARFI DEKRA", watermark_style))

        doc_temp.build(story)
        buffer.seek(0)

        total_width = half_width * 2
        combo_page = new_doc.new_page(width=total_width, height=page_height)

        img_byte_arr = io.BytesIO()
        final_img_pil.save(img_byte_arr, format="PNG")
        combo_page.insert_image(
            fitz.Rect(0, 0, half_width, page_height),
            stream=img_byte_arr.getvalue()
        )

        translated_pdf_doc = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        combo_page.show_pdf_page(
            fitz.Rect(half_width, 0, total_width, page_height),
            translated_pdf_doc, 0
        )
        gc.collect()

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()

    progress_bar.empty()
    status_text.empty()

    output_buffer.seek(0)
    full_text_combined = "\n\n".join(all_translated_texts)
    return output_buffer.getvalue(), full_text_combined


# ----------------------------------------------------
# 4. الواجهة الرئيسية
# ----------------------------------------------------
st.set_page_config(page_title="MEDICAL TRANSLATOR AGENT", page_icon="🩺", layout="wide")

st.title("🩺 MEDICAL TRANSLATOR AGENT")
st.caption("Advanced Medical & Population Genetics Translation Engine | **BY CHARFI DEKRA**")

tab_text, tab_file = st.tabs(["📝 ترجمة نص مباشر", "📄 ترجمة ملف (PDF, Scanned PDF, PowerPoint)"])

with tab_text:
    st.subheader("ترجمة النص الطبي المباشر وتصحيح المصطلحات")
    user_input_text = st.text_area(
        label="أدخل النص المراد ترجمته (فرنسي / عربي):",
        height=200,
        placeholder="أكتب أو ألصق النص هنا...",
    )

    if st.button("ترجمة النص", key="btn_translate_text"):
        if user_input_text.strip():
            with st.spinner("جاري الترجمة والتصحيح الأكاديمي..."):
                result = translate_document(user_input_text)
                if result.startswith("Error") or result.startswith("Translation Service Error"):
                    st.error(result)
                else:
                    st.success("✅ تمت الترجمة بنجاح!")
                    st.text_area(label="النص المترجم والمصحح:", value=result, height=250)
        else:
            st.warning("يرجى إدخال نص أولاً.")

with tab_file:
    st.subheader("رفع وترجمة الملفات (يدعم جميع الأنواع)")
    uploaded_file = st.file_uploader(
        "قم برفع الملف (PDF عادي، PDF ممسوح ضوئياً، PowerPoint .pptx)", 
        type=["pdf", "pptx", "ppt"]
    )

    if uploaded_file is not None:
        st.success("تم استلام الملف بنجاح!")

        if st.button("ترجمة المستند وتوليد PDF المقسوم", key="btn_translate_file"):
            azkar_container = st.empty()
            with azkar_container.container():
                components.html(AZKAR_HTML, height=200)

            try:
                final_pdf_bytes, combined_text = generate_side_by_side_pdf_safe(
                    uploaded_file, translate_document
                )
                
                azkar_container.empty()
                st.success("🎉 اكتملت المعالجة بنجاح!")

                st.text_area(label="معاينة النص المترجم والمصحح:", value=combined_text, height=250)

                st.download_button(
                    label="📥 تحميل الملف المترجم المقسوم (PDF) - BY CHARFI DEKRA",
                    data=final_pdf_bytes,
                    file_name=f"translated_BY_CHARFI_DEKRA_{uploaded_file.name.split('.')[0]}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                azkar_container.empty()
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
