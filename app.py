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

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


# ----------------------------------------------------
# 1. كود لعبة الدودة (Snake Game)
# ----------------------------------------------------
SNAKE_GAME_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {
    background-color: #0e1117;
    color: #ffffff;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 0;
    padding: 10px;
  }
  h4 { margin: 5px 0 10px 0; color: #ff4b4b; }
  canvas {
    border: 2px solid #484848;
    background-color: #161b22;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }
  .info {
    margin-top: 8px;
    font-size: 13px;
    color: #b0b0b0;
  }
</style>
</head>
<body>
  <h4>🎮 تسلَّ بـ "لعبة الثعبان" أثناء معالجة مستندك!</h4>
  <canvas id="gameCanvas" width="320" height="240"></canvas>
  <div class="info">استخدم أسهم اللوحة (⬅️ ⬆️ ⬇️ ➡️) للتحكم</div>

<script>
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");

  const grid = 16;
  let count = 0;
  let score = 0;

  let snake = {
    x: 160, y: 120, dx: grid, dy: 0, cells: [], maxCells: 4
  };

  let apple = { x: 320 - grid * 3, y: 240 - grid * 3 };

  function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min)) + min;
  }

  function gameLoop() {
    requestAnimationFrame(gameLoop);
    if (++count < 5) return;
    count = 0;

    ctx.clearRect(0,0,canvas.width,canvas.height);

    snake.x += snake.dx;
    snake.y += snake.dy;

    if (snake.x < 0) snake.x = canvas.width - grid;
    else if (snake.x >= canvas.width) snake.x = 0;

    if (snake.y < 0) snake.y = canvas.height - grid;
    else if (snake.y >= canvas.height) snake.y = 0;

    snake.cells.unshift({x: snake.x, y: snake.y});

    if (snake.cells.length > snake.maxCells) {
      snake.cells.pop();
    }

    ctx.fillStyle = '#ff4b4b';
    ctx.fillRect(apple.x, apple.y, grid-1, grid-1);

    ctx.fillStyle = '#00e676';
    snake.cells.forEach(function(cell, index) {
      ctx.fillRect(cell.x, cell.y, grid-1, grid-1);

      if (cell.x === apple.x && cell.y === apple.y) {
        snake.maxCells++;
        score += 10;
        apple.x = getRandomInt(0, canvas.width / grid) * grid;
        apple.y = getRandomInt(0, canvas.height / grid) * grid;
      }

      for (let i = index + 1; i < snake.cells.length; i++) {
        if (cell.x === snake.cells[i].x && cell.y === snake.cells[i].y) {
          snake.x = 160; snake.y = 120; snake.cells = []; snake.maxCells = 4;
          snake.dx = grid; snake.dy = 0; score = 0;
          apple.x = getRandomInt(0, canvas.width / grid) * grid;
          apple.y = getRandomInt(0, canvas.height / grid) * grid;
        }
      }
    });

    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    ctx.fillText('النتيجة: ' + score, 10, 20);
  }

  window.addEventListener('keydown', function(e) {
    if ([37, 38, 39, 40].indexOf(e.keyCode) > -1) e.preventDefault();

    if (e.which === 37 && snake.dx === 0) { snake.dx = -grid; snake.dy = 0; }
    else if (e.which === 38 && snake.dy === 0) { snake.dy = -grid; snake.dx = 0; }
    else if (e.which === 39 && snake.dx === 0) { snake.dx = grid; snake.dy = 0; }
    else if (e.which === 40 && snake.dy === 0) { snake.dy = grid; snake.dx = 0; }
  });

  requestAnimationFrame(gameLoop);
</script>
</body>
</html>
"""


# ----------------------------------------------------
# 2. الترجمة عبر الرؤية البصرية (للمستندات الممسوحة ضوئياً)
# ----------------------------------------------------
def translate_scanned_image(img_pil: Image.Image) -> str:
    """استخراج النص والترجمة مباشرة من الصور عبر Groq Vision"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY missing."

    # تحويل الصورة إلى Base64
    buffered = io.BytesIO()
    img_pil.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    system_prompt = (
        "You are an elite Clinical Genetics Professor and Expert Medical Translator.\n"
        "Transcribe and translate all text present in this medical image/page into highly accurate academic English.\n"
        "STRICT RULES:\n"
        "1. Preserve all clinical and genetic terms (Hardy-Weinberg genotypes AA, Aa, aa).\n"
        "2. Do not omit any medical content.\n"
        "3. Output ONLY the translated academic English text without preamble."
    )

    try:
        response = completion(
            model="groq/llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Vision Translation Error: {str(e)}"


# ----------------------------------------------------
# 3. معالجة الصفحات الذكية (نص عادي + Scan)
# ----------------------------------------------------
def process_single_page(args):
    page_num, page_bytes, translator_func = args
    
    doc = fitz.open(stream=page_bytes, filetype="pdf")
    orig_page = doc[0]

    extracted_text = orig_page.get_text("text").strip()
    
    # دقة متوازنة وممتازة
    pix = orig_page.get_pixmap(dpi=120)
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

    # إذا كان النص موجوداً رقمياً نستخدم الترجمة السريعة، وإذا كان Scan نستخدم نموذج الرؤية Vision
    if extracted_text and len(extracted_text) > 20:
        translated_text = translator_func(extracted_text)
    else:
        # حل مشكلة Scan: معالجة الصورة بـ Vision Model
        translated_text = translate_scanned_image(img_pil)

    width = orig_page.rect.width
    height = orig_page.rect.height
    
    doc.close()
    gc.collect()

    return page_num, translated_text, img_pil, width, height


def generate_side_by_side_pdf_safe(uploaded_file, translator_func):
    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(orig_doc)

    tasks = []
    for page_num in range(total_pages):
        single_doc = fitz.open()
        single_doc.insert_pdf(orig_doc, from_page=page_num, to_page=page_num)
        page_bytes = single_doc.write()
        single_doc.close()
        tasks.append((page_num, page_bytes, translator_func))

    orig_doc.close()

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("🚀 جاري معالجة المستند وقراءة الصفحات (بما فيها الـ Scan)...")

    results = [None] * total_pages

    # max_workers=2 لحماية الـ CPU والـ RAM تماماً
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_single_page, task) for task in tasks]
        completed = 0
        for future in futures:
            p_num, trans_text, img_pil, width, height = future.result()
            results[p_num] = (trans_text, img_pil, width, height)
            completed += 1
            progress_bar.progress(completed / total_pages)
            status_text.text(f"⚡ تم إكمال ترجمة {completed} من أصل {total_pages} صفحات...")

    status_text.text("🎨 جاري تجميع ملف الـ PDF النهائي...")

    new_doc = fitz.open()
    all_translated_texts = []

    for page_num, (translated_text, final_img_pil, half_width, page_height) in enumerate(results):
        all_translated_texts.append(f"--- Page {page_num + 1} ---\n{translated_text}")

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
        
        watermark_style = ParagraphStyle(
            "WatermarkStyle", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=7, textColor="#777777", alignment=1, spaceAfter=4
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
            Paragraph("BY DEKRA CHARFI", watermark_style),
            Spacer(1, 4),
            Paragraph(f"--- Translation Page {page_num + 1} ---", title_style)
        ]

        for para in translated_text.split("\n\n"):
            if para.strip():
                formatted = para.strip().replace("\n", "<br/>")
                story.append(Paragraph(formatted, dynamic_style))
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 6))
        story.append(Paragraph("BY DEKRA CHARFI", watermark_style))

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
st.caption("Advanced Medical & Population Genetics Translation Engine | **BY DEKRA CHARFI**")

tab_text, tab_file = st.tabs(["📝 ترجمة نص مباشر", "📄 ترجمة ملف PDF (مع اللعبة والعلامة المائية)"])

with tab_text:
    st.subheader("ترجمة النص الطبي المباشر وتصحيح المعادلات")
    user_input_text = st.text_area(
        label="أدخلي النص المراد ترجمته (فرنسي / عربي):",
        height=200,
        placeholder="أكتبي أو ألصقي النص هنا...",
    )

    if st.button("ترجمة النص", key="btn_translate_text"):
        if user_input_text.strip():
            with st.spinner("جاري الترجمة والتصحيح الأكاديمي..."):
                from main import translate_document
                result = translate_document(user_input_text)
                if result.startswith("Error") or result.startswith("Translation Service Error"):
                    st.error(result)
                else:
                    st.success("✅ تمت الترجمة بنجاح!")
                    st.text_area(label="النص المترجم والمصحح:", value=result, height=250)
        else:
            st.warning("يرجى إدخال نص أولاً.")

with tab_file:
    st.subheader("رفع وترجمة ملف الـ PDF (يدعم الـ Scanned والـ Text)")
    uploaded_file = st.file_uploader(
        "قم برفع ملف الـ PDF الطبي/الجيني", type=["pdf"]
    )

    if uploaded_file is not None:
        st.success("تم استلام الملف بنجاح!")

        if st.button("ترجمة المستند وتوليد PDF المقسوم", key="btn_translate_file"):
            
            game_container = st.empty()
            
            with game_container.container():
                components.html(SNAKE_GAME_HTML, height=330)

            try:
                from main import translate_document
                final_pdf_bytes, combined_text = generate_side_by_side_pdf_safe(
                    uploaded_file, translate_document
                )
                
                game_container.empty()
                st.success("🎉 اكتملت المعالجة بنجاح!")

                st.text_area(label="معاينة النص الإنجليزي المترجم والمصحح:", value=combined_text, height=250)

                st.download_button(
                    label="📥 تحميل الملف المترجم (PDF) - BY DEKRA CHARFI",
                    data=final_pdf_bytes,
                    file_name="translated_genetics_BY_DEKRA_CHARFI.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                game_container.empty()
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
   
