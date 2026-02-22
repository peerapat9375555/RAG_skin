import os
from openai import OpenAI
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# --- 1. การตั้งค่า API ---
API_KEY = "sk_8BB2YyFppfr1z8Sk4mEfgc4AWLDTsjR4nXn2gsiUhAMdMWY1Jv1Yquin9EhSgf46"
BASE_URL = "https://gen.ai.kku.ac.th/api/v1"
MODEL_NAME = "gemini-3.1-pro-preview"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- 2. เตรียมข้อมูล (Knowledge Base) ---
# ในใช้งานจริง คุณอาจจะโหลดจาก PDF หรือ Text ไฟล์
documents = [
    "โรคผื่นภูมิแพ้ผิวหนัง (Atopic Dermatitis) มักมีอาการผิวแห้ง คันมาก และมีผื่นแดงตามข้อพับ",
    "โรคสะเก็ดเงิน (Psoriasis) เป็นโรคอุบัติซ้ำที่มีผื่นหนา ขอบชัด มีสะเก็ดสีเงิน มักพบบริเวณข้อศอกและหัวเข่า",
    "สิว (Acne Vulgaris) เกิดจากการอุดตันของรูขุมขนและความมันบนใบหน้า มีหลายประเภท ได้แก่ สิวอุดตัน สิวอักเสบ สิวไม่มีหัว",
    "สิวอุดตัน (Comedones) แบ่งเป็นสิวหัวดำ (เปิด) และสิวหัวขาว (ปิด) เกิดจากการอุดตันของหลุมขนด้วยไขมันและเซลล์ผิวหนัง",
    "สิวอักเสบ (Inflammatory Acne) มีลักษณะบวมแดง กดเจ็บ แบ่งเป็นสิวตุ่มแดง (Papules) และสิวหัวหนอง (Pustules) เกิดจากแบคทีเรีย C. acnes",
    "สิวฮอร์โมน มักขึ้นบริเวณคาง คอหอย หรือขากรรไกร มักกำเริบในช่วงก่อนหรือระหว่างมีประจำเดือน เกิดจากความไม่สมดุลของฮอร์โมน",
    "สาเหตุของการเกิดสิวหลักๆ ได้แก่ การผลิตน้ำมันมากเกินไป (Sebum), รูขุมขนอุดตัน, แบคทีเรีย, ความเครียด, พักผ่อนไม่เพียงพอ, และอาหารบางชนิด",
    "การรักษาสิวเบื้องต้น: ยาทา Benzoyl Peroxide (BP) ช่วยฆ่าเชื้อแบคทีเรียและลดการอักเสบ, ยาทา Salicylic Acid (BHA) ช่วยผลัดเซลล์ผิวและสลายการอุดตัน",
    "การรักษาสิวด้วยกลุ่มอนุพันธ์วิตามินเอ (Retinoids) ช่วยลดการอุดตัน แต่มักทำให้ผิวแห้งและไวต่อแสง จึงควรทาตอนกลางคืนและใช้มอยเจอร์ไรเซอร์",
    "การดูแลผิวเป็นสิว: ควรล้างหน้า 2 ครั้งต่อวันด้วยคลีนเซอร์สูตรอ่อนโยน ไม่ควรสครับหน้า หลีกเลี่ยงการบีบหรือแกะสิวเพื่อป้องกันการเกิดรอยและหลุมสิว",
    "การเลือกใช้สกินแคร์สำหรับผิวเป็นสิว: ควรเลือกที่มีเครื่องหมาย Non-comedogenic (ไม่อุดตัน), Oil-free และเพิ่มส่วนผสมที่ลดการอักเสบ เช่น Niacinamide, Zinc",
    "รอยสิว (รอยดำ/รอยแดง) สามารถดูแลรักษาได้โดยการใช้ผลิตภัณฑ์ลดเลือนจุดด่างดำ เช่น Vitamin C, Arbutin และต้องทาครีมกันแดดทุกวันเพื่อป้องกันรอยเข้มขึ้น",
    "วิธีการดูแลผิวเบื้องต้น: ควรทาครีมกันแดดทุกวัน และใช้มอยเจอร์ไรเซอร์เพื่อรักษาความชุ่มชื้น ทั้งคนที่เป็นสิวและไม่เป็นสิวก็ควรทำ"
]

# --- 3. สร้าง Vector Database ---
# ใช้ Embedding model ข้ามภาษาที่รองรับภาษาไทยได้ดีขึ้น
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# สร้าง Database จำลองใน Memory (หรือจะเซฟลง Disk ก็ได้)
vectorstore = Chroma.from_texts(
    texts=documents, 
    embedding=embeddings,
    collection_name="skin_knowledge"
)

# --- 4. ฟังก์ชันสำหรับดึงข้อมูลและตอบคำถาม ---
def get_dermatology_response(user_query):
    # ป้องกันกรณี Query ว่างเปล่าทำให้ Vector Store Error
    if not user_query or not str(user_query).strip():
        return "กรุณาพิมพ์คำถามของคุณค่ะ"

    # ก. ค้นหาข้อมูลที่เกี่ยวข้องจากฐานข้อมูล (Retrieval)
    # ค้นหา 4 ประโยคที่ใกล้เคียงที่สุด (เพิ่มจำนวนจาก 2 เป็น 4 เพื่อให้ได้เนื้อหาครอบคลุมขึ้น)
    docs = vectorstore.similarity_search(user_query, k=4)
    # ใส่ (-) หน้าข้อความเพื่อให้อ่านง่ายขึ้น
    context = "\n".join([f"- {d.page_content}" for d in docs])

    # ข. สร้าง Prompt โดยนำ Context ไปใส่ (Augmentation)
    system_prompt = f"""คุณคือผู้ช่วยอัจฉริยะด้านโรคผิวหนัง 
    จงตอบคำถามโดยอ้างอิงและใช้ข้อมูลที่ให้มาใน "ข้อมูลอ้างอิง" ด้านล่างนี้เป็นหลัก
    หากผู้ใช้ถามหาวิธีรักษาหรือดูแล ให้สรุปขั้นตอนจากข้อมูลอ้างอิงเป็นข้อๆ ให้เข้าใจง่าย
    หากไม่มีข้อมูลใดๆ ใน "ข้อมูลอ้างอิง" ที่เกี่ยวข้องกับคำถามเลย ให้ตอบว่าไม่ทราบและแนะนำให้ปรึกษาแพทย์
    ห้ามแต่งข้อมูลขึ้นมาเองเด็ดขาด
    
    ข้อมูลอ้างอิง:
    {context}
    """

    # ค. ส่งคำถามไปที่ Gemini (Generation)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        stream=False,
        temperature=0.1 # ลดอุณหภูมิลงเพื่อให้ตอบตรงตาม Context มากที่สุด
    )
    
    return response.choices[0].message.content

# --- 5. ทดสอบการใช้งาน ---
if __name__ == "__main__":
    print("--- ระบบผู้ช่วยโรคผิวหนัง (RAG) พร้อมใช้งาน ---")
    while True:
        query = input("สอบถามเรื่องผิวหนัง (หรือพิมพ์ exit เพื่อออก): ")
        if query.lower() == 'exit':
            break
            
        result = get_dermatology_response(query)
        print(f"\nคำตอบ: {result}\n")