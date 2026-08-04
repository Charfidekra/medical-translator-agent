"""
app.py
------
واجهة Streamlit للمترجم الطبي. تسمح برفع ملف (txt/pdf)، ضبط إعدادات
سريعة، ومتابعة الترجمة قطعة بقطعة مع عرض متوازي (فرنسي + مصطلحات
مسترجعة على اليسار، إنجليزي مترجم على اليمين).

تشغيل:
    streamlit run app.py
"""

import os

# إيقاف تتبع الخدمة والذاكرة لتفادي التعارض مع ChromaDB و Python 3.14
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
import io
import streamlit as st
from crewai import Crew, Process, LLM
# باقي الأسطر تاع الكود تاعك عادي جداً...



from config import CHUNK_SIZE_WORDS
from main import chunk_text, translate_chunk
from terminology_db import (
    query_relevant_terms,
    build_database_from_csv,
    get_or_create_collection,
    add_single_term,
)
from review_history import save_correction, get_all_corrections, get_stats

st.set_page_config(page_title="المترجم الطبي - فرنسي ⇾ إنجليزي", layout="wide")


# ----------------------------------------------------------------------------
# دوال مساعدة
# ----------------------------------------------------------------------------

import pypdfium2 as pdfium


def extract_text_from_file(uploaded_file) -> str:
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
                "لم يتم العثور على نص قابل للاستخراج. يرجى التأكد من أن الملف ليس صوراً/سكانر."
            )

        return full_text
    else:
        return uploaded_file.getvalue().decode("utf-8")


def terminology_db_is_ready() -> bool:
    try:
        return get_or_create_collection().count() > 0
    except Exception:
        return False


# ----------------------------------------------------------------------------
# الشريط الجانبي (Sidebar) - الإعدادات
# ----------------------------------------------------------------------------

st.sidebar.title("⚙️ الإعدادات")

api_key_input = st.sidebar.text_input(
    "مفتاح Anthropic API",
    type="password",
    value=os.getenv("ANTHROPIC_API_KEY", ""),
    help="يمكن حفظه فملف .env بدل كتابته فكل مرة",
)
if api_key_input:
    os.environ["ANTHROPIC_API_KEY"] = api_key_input

chunk_size = st.sidebar.slider(
    "حجم القطعة (بالكلمات)",
    min_value=100,
    max_value=800,
    value=CHUNK_SIZE_WORDS,
    step=50,
    help="عدد الكلمات في كل قطعة تُترجم دفعة واحدة. أصغر = أدق وأبطأ، أكبر = أسرع وأقل دقة.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📚 قاعدة بيانات المصطلحات")

if terminology_db_is_ready():
    st.sidebar.success("قاعدة البيانات جاهزة ✅")
else:
    st.sidebar.warning("قاعدة البيانات فارغة أو غير مبنية بعد")

if st.sidebar.button("بناء / تحديث قاعدة البيانات من المعجم"):
    with st.spinner("جاري بناء قاعدة البيانات..."):
        try:
            build_database_from_csv(reset=True)
            st.sidebar.success("تم بناء قاعدة البيانات بنجاح!")
        except Exception as e:
            st.sidebar.error(f"خطأ: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("📋 سجل المراجعة البشرية")
_stats = get_stats()
st.sidebar.metric("مجموع المراجعات", _stats["total"])
col_a, col_b = st.sidebar.columns(2)
col_a.metric("تصحيحات فعلية", _stats["edited"])
col_b.metric("مصطلحات جديدة", _stats["new_terms"])

page = st.sidebar.radio("📄 الصفحة", ["🔄 المترجم", "📋 سجل المراجعات الكامل"])

st.sidebar.markdown("---")
st.sidebar.caption(
    "💡 كل قطعة نص تترجم عبر 3 وكلاء متتالية: "
    "Translator ⇾ Terminology Checker ⇾ Clinical Proofreader"
)


# ----------------------------------------------------------------------------
# صفحة: سجل المراجعات الكامل
# ----------------------------------------------------------------------------

if page == "📋 سجل المراجعات الكامل":
    st.title("📋 سجل المراجعة البشرية الكامل")
    st.caption("كل التصحيحات المحفوظة، الأحدث أولاً")

    show_edited_only = st.checkbox("عرض التصحيحات الفعلية فقط (استبعاد التأكيدات بلا تعديل)")
    corrections = get_all_corrections(edited_only=show_edited_only)

    if not corrections:
        st.info("ما كاين حتى تصحيح محفوظ بعد. رجعي لصفحة 'المترجم' وابدئي المراجعة.")
    else:
        for c in corrections:
            label = "✏️ معدّل" if c["was_edited"] else "✅ مؤكد بلا تعديل"
            with st.expander(f"#{c['id']} - القطعة {c['chunk_num']} - {label} - {c['created_at'][:19]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🇫🇷 النص الأصلي**")
                    st.write(c["source_text"])
                    st.markdown("**🤖 ترجمة الـ AI**")
                    st.write(c["ai_translation"])
                with col2:
                    st.markdown("**✅ الترجمة النهائية (بعد المراجعة)**")
                    st.write(c["human_translation"])
                    if c["new_glossary_term_fr"]:
                        st.markdown("**📖 مصطلح جديد أُضيف للمعجم**")
                        st.code(f"{c['new_glossary_term_fr']} -> {c['new_glossary_term_en']}")
    st.stop()  # ما نكملوش لصفحة المترجم إذا كنا فهاد الصفحة


# ----------------------------------------------------------------------------
# الجسم الرئيسي (صفحة المترجم)
# ----------------------------------------------------------------------------

st.title("🩺 المترجم الطبي الذكي")
st.caption("ترجمة نصوص طبية من الفرنسية إلى الإنجليزية بدقة عالية، مدعومة بمعجم مصطلحات (RAG)")

tab_upload, tab_text = st.tabs(["📄 رفع ملف", "✍️ إدخال نص مباشر"])

source_text = ""

with tab_upload:
    uploaded_file = st.file_uploader("ارفعي ملف .txt أو .pdf", type=["txt", "pdf"])
    if uploaded_file is not None:
        source_text = extract_text_from_upload(uploaded_file)
        st.success(f"تم استخراج {len(source_text.split())} كلمة تقريباً من الملف.")

with tab_text:
    direct_text = st.text_area("الصقي النص الفرنسي هنا", height=200)
    if direct_text.strip():
        source_text = direct_text

st.markdown("---")

start_button = st.button("🚀 ابدأ الترجمة", type="primary", disabled=not source_text.strip())

if "translation_results" not in st.session_state:
    st.session_state.translation_results = []

if start_button:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("لازم تدخلي مفتاح Anthropic API فالشريط الجانبي أولاً.")
    else:
        st.session_state.translation_results = []
        chunks = chunk_text(source_text, chunk_size_words=chunk_size)

        progress_bar = st.progress(0, text=f"جاري التحضير... (0/{len(chunks)})")
        results_container = st.container()

        for idx, chunk in enumerate(chunks, start=1):
            progress_bar.progress(
                idx / len(chunks),
                text=f"جاري ترجمة القطعة {idx}/{len(chunks)}...",
            )

            retrieved_terms = query_relevant_terms(chunk)
            translated = translate_chunk(chunk, retrieved_terms)

            st.session_state.translation_results.append(
                {
                    "chunk_num": idx,
                    "source": chunk,
                    "retrieved_terms": retrieved_terms,
                    "translated": translated,
                }
            )

        progress_bar.progress(1.0, text="اكتملت الترجمة ✅")
        st.success(f"تمت ترجمة {len(chunks)} قطعة/قطع بنجاح!")


# ----------------------------------------------------------------------------
# عرض النتائج (متوازي: فرنسي+مصطلحات على اليسار، إنجليزي على اليمين)
# ----------------------------------------------------------------------------

if st.session_state.translation_results:
    st.markdown("## 📊 النتائج")

    # زر تحميل النص الإنجليزي الكامل
    full_translation = "\n\n".join(
        r["translated"] for r in st.session_state.translation_results
    )
    st.download_button(
        "⬇️ تحميل الترجمة الكاملة (.txt)",
        data=full_translation,
        file_name="translated_output.txt",
        mime="text/plain",
    )

    for result in st.session_state.translation_results:
        with st.expander(
            f"القطعة {result['chunk_num']}", expanded=(result["chunk_num"] == 1)
        ):
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("**🇫🇷 النص الفرنسي الأصلي**")
                st.text_area(
                    "source_text_display",
                    value=result["source"],
                    height=200,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"source_{result['chunk_num']}",
                )

                st.markdown("**📖 المصطلحات المسترجعة من المعجم (RAG)**")
                st.code(result["retrieved_terms"], language=None)

            with col_right:
                st.markdown("**🇬🇧 الترجمة الإنجليزية (قابلة للتعديل)**")
                edited_translation = st.text_area(
                    "translated_text_editable",
                    value=result["translated"],
                    height=350,
                    label_visibility="collapsed",
                    key=f"translated_{result['chunk_num']}",
                )

            # ---- قسم المراجعة البشرية ----
            st.markdown("##### ✏️ المراجعة والتصحيح")

            with st.expander("➕ إضافة مصطلح جديد للمعجم (اختياري)"):
                new_term_col1, new_term_col2 = st.columns(2)
                new_term_fr = new_term_col1.text_input(
                    "المصطلح بالفرنسية", key=f"new_term_fr_{result['chunk_num']}"
                )
                new_term_en = new_term_col2.text_input(
                    "المقابل بالإنجليزية", key=f"new_term_en_{result['chunk_num']}"
                )

            save_col1, save_col2 = st.columns([1, 3])
            if save_col1.button("💾 حفظ التصحيح", key=f"save_{result['chunk_num']}"):
                save_correction(
                    chunk_num=result["chunk_num"],
                    source_text=result["source"],
                    ai_translation=result["translated"],
                    human_translation=edited_translation,
                    new_glossary_term_fr=new_term_fr,
                    new_glossary_term_en=new_term_en,
                )

                if new_term_fr.strip() and new_term_en.strip():
                    try:
                        add_single_term(new_term_fr, new_term_en, domain="", notes="added via human review")
                        save_col2.success(
                            f"تم حفظ التصحيح وإضافة المصطلح '{new_term_fr} -> {new_term_en}' للمعجم! ✅"
                        )
                    except Exception as e:
                        save_col2.warning(f"تم حفظ التصحيح، لكن فشلت إضافة المصطلح للمعجم: {e}")
                else:
                    save_col2.success("تم حفظ التصحيح فسجل المراجعة! ✅")
else:
    st.info("ارفعي ملف أو الصقي نص، ثم اضغطي 'ابدأ الترجمة' لرؤية النتائج هنا.")  


import streamlit as st
from pypdf import PdfReader
from main import translate_document


def extract_text_from_file(uploaded_file) -> str:
    """استخراج النص سواء كان الملف .txt أو .pdf"""
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        # قراءة صفحات ملف الـ PDF واستخراج النصوص
        pdf_reader = PdfReader(uploaded_file)
        extracted_text = []
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(page_text)

        full_text = "\n\n".join(extracted_text)

        if not full_text.strip():
            raise ValueError(
                "لم يتم العثور على نص مكتوب داخل ملف الـ PDF (قد يكون الملف عبارة عن صور/سكانر)."
            )

        return full_text

    else:
        # للملفات النصية العادية .txt
        return uploaded_file.getvalue().decode("utf-8")


# ----------------------------------------------------
# جزء واجهة Streamlit لرفع الملف وترجمته
# ----------------------------------------------------
st.title("🩺 Medical French-to-English Translator")

uploaded_file = st.file_uploader(
    "قم برفع ملف طبّي (PDF أو TXT)", type=["pdf", "txt"]
)

if uploaded_file is not None:
    try:
        source_text = extract_text_from_file(uploaded_file)
        st.success(
            f"تم استخراج النص بنجاح! ({len(source_text.split())} كلمة)"
        )

        # عرض جزء من النص المستخرج للتأكد
        with st.expander("عرض النص المستخرج من الملف"):
            st.text_area("النصر الأصلي", source_text, height=200)

        if st.button("ترجمة المستند"):
            with st.spinner("جاري الترجمة والتدقيق عبر CrewAI..."):
                translated_result = translate_document(source_text)
                st.subheader("الترجمة النهائية:")
                st.write(translated_result)

    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
