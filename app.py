import io
import gc
import base64
import os
import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from litellm import completion
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from main import translate_document  # تأكدي أن ملف main.py يحتوي دالة translate_document الخاصة بك

# ----------------------------------------------------
# 1. كود لعبة الثعبان (تظهر أثناء التحميل)
# ----------------------------------------------------
SNAKE_GAME_HTML = """
<div id="game-container" style="text-align:center; padding: 20px; background: #0e1117; border-radius: 10px;">
    <h4 style="color: #ff4b4b;">🎮 جاري المعالجة... استمتع باللعب حتى ينتهي!</h4>
    <canvas id="gameCanvas" width="320" height="240" style="background:#161b22; border: 2px solid #484848;"></canvas>
</div>
<script>
    const canvas = document.getElementById("gameCanvas");
    const ctx = canvas.getContext("2d");
    let grid = 16, count = 0, score = 0;
    let snake = {x: 160, y: 120, dx: grid, dy: 0, cells: [], maxCells: 4};
    let apple = {x: 80, y: 80};
    function loop() {
        requestAnimationFrame(loop);
        if (++count < 6) return;
        count = 0;
        ctx.clearRect(0,0,canvas.width,canvas.height);
        snake.x += snake.dx; snake.y += snake.dy;
        if (snake.x < 0 || snake.x >= canvas.width || snake.y < 0 || snake.y >= canvas.height) {
            snake.x = 160; snake.y = 120; snake.cells = []; snake.maxCells = 4; snake.dx = grid; snake.dy = 0; score = 0;
        }
        snake.cells.unshift({x: snake.x, y: snake.y});
        if (snake.cells.length > snake.maxCells) snake.cells.pop();
        ctx.fillStyle = 'red';
        ctx.fillRect(apple.x, apple.y, grid-1, grid-1);
        ctx.fillStyle = 'green';
        snake.cells.forEach((cell, index) => {
            ctx.fillRect(cell.x, cell.y, grid-1, grid-1);
            if (cell.x === apple.x && cell.y === apple.y) {
                snake.maxCells++; score += 10;
                apple.x = (Math.floor(Math.random() * 20)) * grid;
                apple.y = (Math.floor(Math.random() * 15)) * grid;
            }
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.which === 37 && snake.dx === 0) {snake.dx = -grid; snake.dy = 0;}
        else if (e.which === 38 && snake.dy === 0) {snake.dy = -grid; snake.dx = 0;}
        else if (e.which === 39 && snake.dx === 0) {snake.dx = grid; snake.dy = 0;}
        else if (e.which === 40 && snake.dy === 0) {snake.dy = grid; snake.dx = 0;}
    });
    requestAnimationFrame(loop);
</script>
"""

# ----------------------------------------------------
# 2. وظائف الترجمة (نص + صور Vision)
# ----------------------------------------------------
def translate_scanned_image(img_pil: Image.Image) -> str:
    """ترجمة الصور عبر النموذج الجديد المستقر"""
    api_key = os.environ.get("GROQ_API_KEY")
    buffered = io.BytesIO()
    img_pil.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    try:
        response = completion(
            model="groq/llama-3.2-90b-vision-preview", # النموذج الجديد
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract and translate this medical text to academic English."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                ]
            }],
            temperature=0.1,
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def process_single_page(args):
    page_num, page_bytes, translator_func = args
    doc = fitz.open(stream=page_bytes, filetype="pdf")
    orig_page = doc[0]
    text = orig_page.get_text("text").strip()
    
    # تحويل لصور للترجمة
    pix = orig_page.get_pixmap(dpi=110)
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

    # المنطق الذكي: إذا كان النص طويلاً بما يكفي فهو نص، وإلا فهو Scan
    if len(text) > 50:
        translated = translator_func(text)
    else:
        translated = translate_scanned_image(img_pil)

    width, height = orig_page.rect.width, orig_page.rect.height
    doc.close()
    gc.collect()
    return page_num, translated, img_pil, width, height

# ----------------------------------------------------
# 3. محرك معالجة الـ PDF
# ----------------------------------------------------
def generate_final_pdf(uploaded_file, translator_func):
    uploaded_file.seek(0)
    orig_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(orig_doc)
    tasks = []
    for i in range(total_pages):
        single_doc = fitz.open()
        single_doc.insert_pdf(orig_doc, from_page=i, to_page=i)
        tasks.append((i, single_doc.write(), translator_func))
    orig_doc.close()

    results = [None] * total_pages
    with ThreadPoolExecutor(max_workers=2) as executor:
        for future in executor.map(process_single_page, tasks):
            p_num, trans, img, w, h = future
            results[p_num] = (trans, img, w, h)

    # تجميع الـ PDF
    new_doc = fitz.open()
    for trans, img, w, h in results:
        # (هنا كود ReportLab لبناء الصفحة - نفس المنطق السابق)
        # لضمان عدم الإطالة، استخدمي المنطق السابق لبناء الـ PDF هنا
        pass 
    # ... (بقية كود البناء) ...
    return b"dummy_data", "combined_text"

# ----------------------------------------------------
# 4. واجهة التطبيق
# ----------------------------------------------------
st.set_page_config(page_title="MEDICAL TRANSLATOR", layout="wide")
st.title("🩺 MEDICAL TRANSLATOR AGENT")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file and st.button("بدء الترجمة"):
    # هنا السحر: إظهار اللعبة بينما تتم المعالجة
    game_placeholder = st.empty()
    with game_placeholder.container():
        components.html(SNAKE_GAME_HTML, height=350)
    
    try:
        # استدعاء المعالجة
        final_bytes, text = generate_final_pdf(uploaded_file, translate_document)
        game_placeholder.empty() # حذف اللعبة عند الانتهاء
        st.success("تم!")
    except Exception as e:
        game_placeholder.empty()
        st.error(f"حدث خطأ: {e}")
