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
    "สิว (Acne Vulgaris) เกิดจากการอุดตันของรูขุมขนและความมันบนใบหน้า การรักษาเบื้องต้นใช้ Benzoyl Peroxide",
    "โรคสะเก็ดเงิน (Psoriasis) เป็นโรคอุบัติซ้ำที่มีผื่นหนา ขอบชัด มีสะเก็ดสีเงิน มักพบบริเวณข้อศอกและหัวเข่า",
    "วิธีการดูแลผิวเบื้องต้น: ควรทาครีมกันแดดทุกวัน และใช้มอยเจอร์ไรเซอร์เพื่อรักษาความชุ่มชื้น"
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
    # ก. ค้นหาข้อมูลที่เกี่ยวข้องจากฐานข้อมูล (Retrieval)
    # ค้นหา 2 ประโยคที่ใกล้เคียงที่สุด
    docs = vectorstore.similarity_search(user_query, k=2)
    context = "\n".join([d.page_content for d in docs])

    # ข. สร้าง Prompt โดยนำ Context ไปใส่ (Augmentation)
    system_prompt = f"""คุณคือผู้ช่วยอัจฉริยะด้านโรคผิวหนัง 
    จงตอบคำถามโดยใช้ข้อมูลที่ให้มาด้านล่างนี้เท่านั้น หากไม่มีข้อมูลให้ตอบว่าไม่ทราบและแนะนำให้ปรึกษาแพทย์
    
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
        stream=False
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