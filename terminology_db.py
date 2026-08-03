"""
terminology_db.py
------------------
قاعدة بيانات مصطلحات طبية (فرنسي-إنجليزي) مبنية بـ ChromaDB.

الفكرة:
1. نقرأو المعجم من ملف CSV (french_term, english_term, domain, notes).
2. نبنيو "مجموعة" (collection) فـ ChromaDB، كل مصطلح فرنسي يتخزن مع
   الـ embedding ديالو، ومعاه بيانات إضافية (metadata): الترجمة، المجال، ملاحظات.
3. عند الترجمة، قبل ما نبعثو القطعة (chunk) للـ Translator Agent، ندورو
   بحث بالتشابه الدلالي (semantic similarity) باش نلقاو أي مصطلح من
   المعجم موجود احتمالياً فالنص، ونعطيوهم كسياق موثوق (Retrieval).

ملاحظة: هذا بحث "استرجاعي تقريبي" مبني على قرب المعنى، مو مطابقة حرفية
فقط، لهذا يقدر يلقى مصطلحات حتى لو مكتوبة بصيغة مختلفة شوية فالنص.
"""

import os
import csv
import chromadb
from chromadb.utils import embedding_functions
from config import TERMINOLOGY_DB_PATH, TERMINOLOGY_SEED_FILE

COLLECTION_NAME = "medical_terms_fr_en"

# نستعملو embedding function مجانية ومحلية (لا تحتاج API key) باش
# البحث فالمعجم يخدم حتى بلا اتصال بالإنترنت أو تكلفة إضافية.
_embedding_fn = embedding_functions.DefaultEmbeddingFunction()


def get_client():
    os.makedirs(TERMINOLOGY_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=TERMINOLOGY_DB_PATH)


def get_or_create_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )


def build_database_from_csv(csv_path: str = TERMINOLOGY_SEED_FILE, reset: bool = False):
    """
    يقرأ المعجم من ملف CSV ويبنيه/يحدثه فـ ChromaDB.
    reset=True يمسح المجموعة القديمة ويبنيها من جديد بالكامل.
    """
    client = get_client()

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # ما كانتش موجودة أصلاً

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )

    ids, documents, metadatas = [], [], []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            french_term = row["french_term"].strip()
            if not french_term:
                continue
            ids.append(f"term_{idx}")
            documents.append(french_term)  # النص اللي راح يتحول لـ embedding
            metadatas.append(
                {
                    "english_term": row["english_term"].strip(),
                    "domain": row.get("domain", "").strip(),
                    "notes": row.get("notes", "").strip(),
                }
            )

    if not ids:
        print("[WARN] ملف الـ CSV فارغ أو ما فيهش بيانات صالحة.")
        return

    # نستعملو upsert باش نقدرو نعاودو نشغل الدالة بلا ما نديرو duplicate
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"[INFO] تم إدراج/تحديث {len(ids)} مصطلح فقاعدة البيانات.")


def query_relevant_terms(text: str, n_results_per_word: int = 2, max_results: int = 15) -> str:
    """
    يبحث فقاعدة البيانات عن المصطلحات الأقرب دلالياً للنص المُعطى،
    ويرجع نتيجة كنص جاهز يتحط فـ prompt الوكيل (RAG_QUERY_TEMPLATE).

    ملاحظة: بما أن ChromaDB ما يدعمش بحث "هل هذا المصطلح موجود فهاد
    النص الطويل"، كنديرو بحث بالتشابه الدلالي للنص كامل (كـ query
    وحدة)، وهذا كافي فالمعظم لأن نموذج الـ embedding يمسك المعنى
    العام للفقرة ويقارنه بمعنى كل مصطلح فالمعجم.
    """
    collection = get_or_create_collection()

    if collection.count() == 0:
        return "(قاعدة بيانات المصطلحات فارغة - شغلي build_database_from_csv أولاً)"

    results = collection.query(
        query_texts=[text],
        n_results=min(max_results, collection.count()),
    )

    if not results["documents"] or not results["documents"][0]:
        return "(لا توجد مصطلحات ذات صلة)"

    lines = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        lines.append(
            f"- {doc} -> {meta['english_term']}"
            + (f" [{meta['domain']}]" if meta.get("domain") else "")
            + (f" (note: {meta['notes']})" if meta.get("notes") else "")
        )

    return "\n".join(lines)


def add_single_term(french_term: str, english_term: str, domain: str = "", notes: str = ""):
    """
    يزيد مصطلح واحد جديد لقاعدة البيانات (Chroma) وللمعجم (CSV) فآن واحد،
    بلا ما يعاود يبني القاعدة كاملة. يستعمل مبدئياً من نظام المراجعة
    البشرية (review_history.py) لما مستخدم يأكد على مصطلح جديد.
    """
    french_term = french_term.strip()
    english_term = english_term.strip()
    if not french_term or not english_term:
        raise ValueError("لازم يكون عندك french_term و english_term بلا ما يكونوا فارغين.")

    # 1. زيادة المصطلح لقاعدة بيانات Chroma
    collection = get_or_create_collection()
    new_id = f"term_manual_{abs(hash(french_term)) % (10**8)}"
    collection.upsert(
        ids=[new_id],
        documents=[french_term],
        metadatas=[{"english_term": english_term, "domain": domain, "notes": notes}],
    )

    # 2. زيادة المصطلح لملف الـ CSV باش يبقى محفوظ نهائياً حتى لو تمسح قاعدة Chroma
    with open(TERMINOLOGY_SEED_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([french_term, english_term, domain, notes])

    print(f"[INFO] تمت إضافة المصطلح: {french_term} -> {english_term}")



    # تشغيل مباشر لهذا الملف يبني قاعدة البيانات من الصفر
    build_database_from_csv(reset=True)

    # اختبار سريع
    test_text = (
        "Le patient présente une insuffisance rénale aiguë associée à une "
        "hyperglycémie et une légère anémie."
    )
    print("\n[TEST] المصطلحات المسترجعة للنص التجريبي:\n")
    print(query_relevant_terms(test_text))
