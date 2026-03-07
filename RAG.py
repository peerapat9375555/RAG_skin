"""
RAG.py — Retrieval-Augmented Generation for DermaAI
Vector Database: Supabase + pgvector
Embedding: Google Gemini text-embedding-004 (768-dim, via API)
LLM: Gemini via KKU AI Gateway
"""

import os
import requests
from openai import OpenAI
from supabase import create_client, Client

# ── 1. Configuration ──────────────────────────────────────────────────────────

LLM_API_KEY  = os.environ.get("LLM_API_KEY",  "sk_8BB2YyFppfr1z8Sk4mEfgc4AWLDTsjR4nXn2gsiUhAMdMWY1Jv1Yquin9EhSgf46")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://gen.ai.kku.ac.th/api/v1")
LLM_MODEL    = os.environ.get("LLM_MODEL",    "gemini-3.1-pro-preview")

# Embedding API — ใช้ Google Gemini Embedding (ประหยัด RAM, ไม่ต้องโหลดโมเดล)
EMBED_API_KEY  = os.environ.get("EMBED_API_KEY",  "")
EMBED_BASE_URL = os.environ.get("EMBED_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
EMBED_MODEL    = os.environ.get("EMBED_MODEL",    "text-embedding-004")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://rsocwhsekrnpwuejankb.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJzb2N3aHNla3JucHd1ZWphbmtiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3Njk1MDUsImV4cCI6MjA4NzM0NTUwNX0.CPvVpSyXhxSHPhH2Hm_ZHsXdeoxb23pybVhYxhoUwE8")
TABLE_NAME   = "skin_documents"
MATCH_FN     = "match_skin_documents"

# ── 2. Initialise clients ─────────────────────────────────────────────────────

llm_client: OpenAI  = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
embed_client: OpenAI = OpenAI(api_key=EMBED_API_KEY, base_url=EMBED_BASE_URL)
db: Client           = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── 3. Embedding via API ──────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Get embedding vector via API (no local model needed)."""
    try:
        response = embed_client.embeddings.create(
            model=EMBED_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[WARN] Embedding API error: {e}")
        return []


def _embed_many(texts: list[str]) -> list[list[float]]:
    """Get embedding vectors for multiple texts via API."""
    try:
        response = embed_client.embeddings.create(
            model=EMBED_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"[WARN] Embedding API error: {e}")
        return [[] for _ in texts]


# ── 4. Seed initial knowledge ─────────────────────────────────────────────────

_INITIAL_DOCUMENTS = [
    "โรคผื่นภูมิแพ้ผิวหนัง (Atopic Dermatitis) มักมีอาการผิวแห้ง คันมาก และมีผื่นแดงตามข้อพับ",
    "โรคสะเก็ดเงิน (Psoriasis) เป็นโรคอุบัติซ้ำที่มีผื่นหนา ขอบชัด มีสะเก็ดสีเงิน มักพบบริเวณข้อศอกและหัวเข่า",
    "สิว (Acne Vulgaris) เกิดจากการอุดตันของรูขุมขนและความมันบนใบหน้า มีหลายประเภท ได้แก่ สิวอุดตัน สิวอักเสบ สิวไม่มีหัว",
    "สิวอุดตัน (Comedones) แบ่งเป็นสิวหัวดำ (เปิด) และสิวหัวขาว (ปิด) เกิดจากการอุดตันของหลุมขนด้วยไขมันและเซลล์ผิวหนัง",
    "สิวอักเสบ (Inflammatory Acne) มีลักษณะบวมแดง กดเจ็บ แบ่งเป็นสิวตุ่มแดง (Papules) และสิวหัวหนอง (Pustules) เกิดจากแบคทีเรีย C. acnes",
    "สิวฮอร์โมน มักขึ้นบริเวณคาง คอหอย หรือขากรรไกร มักกำเริบในช่วงก่อนหรือระหว่างมีประจำเดือน เกิดจากความไม่สมดุลของฮอร์โมน",
    "สาเหตุของการเกิดสิวหลักๆ ได้แก่ การผลิตน้ำมันมากเกินไป (Sebum), รูขุมขนอุดตัน, แบคทีเรีย, ความเครียด, พักผ่อนไม่เพียงพอ และอาหารบางชนิด",
    "การรักษาสิวเบื้องต้น: ยาทา Benzoyl Peroxide (BP) ช่วยฆ่าเชื้อแบคทีเรียและลดการอักเสบ, ยาทา Salicylic Acid (BHA) ช่วยผลัดเซลล์ผิวและสลายการอุดตัน",
    "การรักษาสิวด้วยกลุ่มอนุพันธ์วิตามินเอ (Retinoids) ช่วยลดการอุดตัน แต่มักทำให้ผิวแห้งและไวต่อแสง จึงควรทาตอนกลางคืนและใช้มอยเจอร์ไรเซอร์",
    "การดูแลผิวเป็นสิว: ควรล้างหน้า 2 ครั้งต่อวันด้วยคลีนเซอร์สูตรอ่อนโยน ไม่ควรสครับหน้า หลีกเลี่ยงการบีบหรือแกะสิวเพื่อป้องกันการเกิดรอยและหลุมสิว",
    "การเลือกใช้สกินแคร์สำหรับผิวเป็นสิว: ควรเลือกที่มีเครื่องหมาย Non-comedogenic (ไม่อุดตัน), Oil-free และเพิ่มส่วนผสมที่ลดการอักเสบ เช่น Niacinamide, Zinc",
    "รอยสิว (รอยดำ/รอยแดง) สามารถดูแลรักษาได้โดยการใช้ผลิตภัณฑ์ลดเลือนจุดด่างดำ เช่น Vitamin C, Arbutin และต้องทาครีมกันแดดทุกวันเพื่อป้องกันรอยเข้มขึ้น",
    "วิธีการดูแลผิวเบื้องต้น: ควรทาครีมกันแดดทุกวัน และใช้มอยเจอร์ไรเซอร์เพื่อรักษาความชุ่มชื้น ทั้งคนที่เป็นสิวและไม่เป็นสิวก็ควรทำ",
]


def _seed_if_empty() -> None:
    """Insert initial knowledge base documents if the table is empty."""
    try:
        resp = db.table(TABLE_NAME).select("id", count="exact").limit(1).execute()
        count = resp.count if resp.count is not None else len(resp.data)
        if count == 0:
            print("[INFO] Seeding initial knowledge base into Supabase ...")
            vectors = _embed_many(_INITIAL_DOCUMENTS)
            if not vectors or not vectors[0]:
                print("[WARN] Embedding API returned empty vectors. Skipping seed.")
                return
            rows = [
                {
                    "content":   doc,
                    "embedding": vec,
                    "source":    "initial_seed",
                    "metadata":  {"index": i, "type": "seed"},
                }
                for i, (doc, vec) in enumerate(zip(_INITIAL_DOCUMENTS, vectors))
            ]
            db.table(TABLE_NAME).insert(rows).execute()
            print(f"[OK]   Seeded {len(_INITIAL_DOCUMENTS)} initial documents.")
        else:
            # ตรวจสอบ dimension ให้ตรงกัน — ถ้าไม่ตรงจะ reseed ใหม่
            try:
                sample = db.table(TABLE_NAME).select("embedding").limit(1).execute()
                if sample.data and sample.data[0].get("embedding"):
                    old_dim = len(sample.data[0]["embedding"])
                    test_vec = _embed("test")
                    if test_vec:
                        new_dim = len(test_vec)
                        if old_dim != new_dim:
                            print(f"[WARN] Dimension mismatch: old={old_dim}, new={new_dim}. Re-seeding...")
                            db.table(TABLE_NAME).delete().neq("id", 0).execute()
                            _seed_if_empty()
                            return
            except Exception:
                pass
            print(f"[OK]   Supabase vector DB ready ({count} documents).")
    except Exception as e:
        print(f"[WARN] Could not check/seed DB: {e}")


# ── 5. Core RAG function ──────────────────────────────────────────────────────

_seeded = False

def _ensure_seeded():
    global _seeded
    if not _seeded:
        _seed_if_empty()
        _seeded = True


def get_dermatology_response(user_query: str) -> str:
    """RAG pipeline: embed query → vector search → LLM generate."""
    _ensure_seeded()

    if not user_query or not str(user_query).strip():
        return "กรุณาพิมพ์คำถามของคุณค่ะ"

    # (a) Embed query via API
    query_vector = _embed(user_query)

    # (b) Retrieve from Supabase
    context = "(ไม่พบข้อมูลที่เกี่ยวข้องในฐานข้อมูล)"
    if query_vector:
        try:
            result = db.rpc(
                MATCH_FN,
                {
                    "query_embedding": query_vector,
                    "match_count":     4,
                    "match_threshold": 0.2,
                }
            ).execute()
            docs = result.data or []
            if docs:
                context = "\n".join([f"- {d['content']}" for d in docs])
        except Exception as e:
            print(f"[WARN] Supabase retrieval error: {e}")
    else:
        # Fallback: use all seed documents as context if embedding fails
        context = "\n".join([f"- {doc}" for doc in _INITIAL_DOCUMENTS])

    # (c) Generate with LLM
    system_prompt = f"""คุณคือผู้ช่วยอัจฉริยะด้านโรคผิวหนัง
จงตอบคำถามโดยอ้างอิงและใช้ข้อมูลที่ให้มาใน "ข้อมูลอ้างอิง" เป็นหลัก
หากผู้ใช้ถามหาวิธีรักษาหรือดูแล ให้สรุปขั้นตอนเป็นข้อๆ ให้เข้าใจง่าย
หากไม่มีข้อมูลที่เกี่ยวข้อง ให้บอกว่าไม่ทราบและแนะนำให้ปรึกษาแพทย์
ห้ามแต่งข้อมูลขึ้นมาเองเด็ดขาด

ข้อมูลอ้างอิง:
{context}
"""

    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_query},
        ],
        stream=False,
        temperature=0.1
    )

    return response.choices[0].message.content


# ── 6. Embed new documents ────────────────────────────────────────────────────

def embed_documents(raw_text: str, chunk_size: int = 500, source: str = "upload") -> dict:
    """Split and embed new documents into Supabase."""
    if not raw_text or not raw_text.strip():
        raise ValueError("ข้อความว่างเปล่า ไม่สามารถ Embed ได้")

    # Simple chunking by newline
    chunks = [c.strip() for c in raw_text.strip().split("\n") if c.strip()]
    if not chunks:
        raise ValueError("ไม่สามารถแบ่ง Chunk ได้")

    vectors = _embed_many(chunks)
    if not vectors or not vectors[0]:
        raise ValueError("Embedding API ไม่สามารถสร้าง vector ได้")

    rows = [
        {
            "content":   chunk,
            "embedding": vector,
            "source":    source,
            "metadata":  {"chunk_index": i, "chunk_count": len(chunks)},
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    db.table(TABLE_NAME).insert(rows).execute()
    return {
        "chunks_added": len(chunks),
        "total_chars":  len(raw_text),
        "message":      f"เพิ่ม {len(chunks)} chunks สำเร็จ"
    }


# ── 7. CLI test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("--- DermaAI RAG System ---")
    _ensure_seeded()
    while True:
        query = input("สอบถาม (exit เพื่อออก): ")
        if query.lower() == "exit":
            break
        print(f"\nคำตอบ: {get_dermatology_response(query)}\n")