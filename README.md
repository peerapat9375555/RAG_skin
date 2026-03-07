# DermaAI Chatbot Service (RAG Pipeline)

โปรเจ็กต์นี้ถูกออกแบบด้วยสถาปัตยกรรมแบบ **Microservices** เพื่อแยกการทำงานแต่ละส่วนออกจากกันอย่างอิสระ ทำให้ง่ายต่อการจัดการทรัพยากร (특히 RAM บน Free Tier) และการอัปเดตระบบในอนาคต

ระบบประกอบด้วย 4 ส่วนหลัก:

---

## 🏗️ 1. Frontend Web Service (UI)

- **เครื่องมือ:** React, Vite, Vercel
- **หน้าที่:** เป็นหน้าบ้านรับรูปภาพจากผู้ใช้ และมีหน้าต่างแชทสำหรับพูดคุย
- **การเชื่อมต่อ:**
  - `VITE_MODEL_URL` → ส่งรูปไปยัง **Model Service**
  - `VITE_CHATBOT_URL` → ส่งข้อความไปยัง **Chatbot Service**

---

## 🧠 2. Model Service (Skin Analysis)

- **เครื่องมือ:** Python, Flask, ONNX Runtime, Render (Free Tier)
- **Repository:** `peerapat9375555/SE`
- **หน้าที่:** รับรูปภาพผิวหนังและทำนายความเสี่ยงของโรค
- **ทำไมต้องเป็น Microservice แยก?**
  - โมเดล PyTorch ทั่วไปกิน RAM สูง (> 600MB) ซึ่งเกินข้อจำกัดของ Render Free Tier (512MB)
  - เราจึง **แยก Service นี้ออกมา** แปลงโมเดลเป็น `.onnx` และใช้ `onnxruntime` รันบน CPU (ใช้ RAM เพียง ~80-120MB)
- **Endpoint หลัก:** `POST /api/predict` รับไฟล์รูปภาพแล้วคืนค่าผลการทำนาย (เปอร์เซ็นต์ความเสี่ยง)

---

## 🤖 3. Chatbot Service (RAG Pipeline) - [Current Repo]

- **เครื่องมือ:** Python, Flask, Supabase, Google Gemini API, KKU API Gateway, Render (Free Tier)
- **Repository:** `peerapat9375555/RAG_skin`
- **หน้าที่:**
  1. ให้บริการหน้าเพิ่มข้อมูลเข้าฐานข้อมูล (`/embed`)
  2. ตอบคำถามผู้ใช้ผ่านแชทโดยใช้เทคนิค RAG (Retrieval-Augmented Generation)
- **ทำไมต้องเป็น Microservice แยก?**
  - งานด้าน NLP (เช่น Embedding, Reranking, LLM) กิน Memory และ Compute Power สูงลิ่ว
  - หากรวมกับฝั่ง Model Service หรือใช้ Model ในเครื่อง (Local HuggingFace model) จะทำให้ OOM (Out of Memory) ทันที
  - เราจึงแยกมาอีก Service และ **เปลี่ยนไปใช้ API ทั้งหมด** เพื่อให้ RAM ไม่เกิน 100MB

### 🔄 กระบวนการ RAG Pipeline ใน Chatbot Service

เมื่อผู้ใช้พิมพ์คำถามมา 1 ประโยค ระบบทำงานตามลำดับนี้:

1. **Embedding (Google Gemini):**
   - รับคำถามผู้ใช้ ไปแปลงเป็นเวกเตอร์ (768 มิติ) ผ่าน `text-embedding-004`
   - _ใช้คีย์: `EMBED_API_KEY` (Google AI Studio)_

2. **Vector Retrieval (Supabase pgvector):**
   - นำเวกเตอร์ไปค้นหาเอกสารที่มีความหมายใกล้เคียงที่สุดใน Supabase
   - ดึงข้อมูลเบื้องต้นมา **8 เอกสาร (Candidate)**

3. **Reranking (KKU LLM):**
   - ส่ง 8 เอกสาร พร้อมคำถาม ไปให้ LLM (Gemini) ช่วย **ให้คะแนน (Score)** ความเกี่ยวข้อง
   - คัดกรองและเลือกเฉพาพ **4 เอกสารที่ตอบตรงคำถามที่สุด**
   - _ใช้คีย์: `RERANK_API_KEY` (KKU Gateway)_

4. **Generation (KKU LLM):**
   - นำ 4 เอกสารสุดท้าย ป้อนเป็น `Context` (ข้อมูลอ้างอิง) ให้ LLM อ่าน
   - สั่งให้ LLM คัดลอก/สรุปเนื้อหาจาก Context เพื่อตอบคำถามผู้ใช้
   - _ใช้คีย์: `LLM_API_KEY` (KKU Gateway)_

- **Endpoint หลัก:** `POST /api/chat` , `POST /api/embed`

---

## 🗄️ 4. Vector Database

- **เครื่องมือ:** Supabase (PostgreSQL + `pgvector` extension)
- **หน้าที่:**
  - เก็บข้อมูลเอกสารด้านโรคผิวหนังในรูปแบบเวกเตอร์ 768 มิติ (สร้างจาก Google Gemini Embedding)
  - มีฟังก์ชัน RPC `match_skin_documents` สำหรับทำ Cosine Similarity Search ที่รวดเร็ว

---

## 🔗 ภาพรวมการไหลของข้อมูล (Data Flow)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ffffff', 'edgeLabelBackground':'#e8e8e8', 'tertiaryColor': '#f4f4f4'}}}%%
graph TD

    %% ----------------------------------------------------
    %% User Layer
    %% ----------------------------------------------------
    subgraph UserSpace ["👥 User Space"]
        User(("👤 User\n(Mobile / Web)"))
    end

    %% ----------------------------------------------------
    %% Frontend Layer
    %% ----------------------------------------------------
    subgraph Vercel ["⚡ Vercel (Frontend Service)"]
        UI["💻 React Vite App\n(dermaai.vercel.app)"]
        UI_Img[/"📤 Upload Image"/]
        UI_Chat[/"💬 Chat Query"/]

        UI --- UI_Img
        UI --- UI_Chat
    end

    %% ----------------------------------------------------
    %% Backend Layer (Render)
    %% ----------------------------------------------------
    subgraph Render ["☁️ Render (Backend Microservices)"]

        %% Service 1: Model
        subgraph ModelService ["🧠 Model Service (peerapat9375555/SE)"]
            API1["API: /api/predict"]
            ONNX[{"⚙️ ONNX Runtime\n(CPU Inference)"}]
            API1 --> ONNX
        end

        %% Service 2: Chatbot (RAG)
        subgraph ChatbotService ["🤖 Chatbot Service (peerapat9375555/RAG_skin)"]
            API2["API: /api/chat"]

            subgraph RAGipeline ["⚡ RAG Pipeline"]
                EmbedProcess["1️⃣ Embedding\n(Text ➡️ Vector)"]
                SearchProcess["2️⃣ Vector Retrieval\n(Fetch Top-8)"]
                RerankProcess["3️⃣ LLM Reranking\n(Select Top-4)"]
                GenProcess["4️⃣ Generation\n(Context + Prompt)"]

                EmbedProcess --> SearchProcess
                SearchProcess --> RerankProcess
                RerankProcess --> GenProcess
            end

            API2 --> EmbedProcess
        end
    end

    %% ----------------------------------------------------
    %% External APIs & Databases
    %% ----------------------------------------------------
    subgraph External ["🌐 External APIs & Storage"]

        SupaDB[("🗄️ Supabase DB\n(pgvector)")]

        subgraph GoogleAPI ["🔹 Google AI Studio"]
            GeminiEmbed(("Gemini\ntext-embedding-004"))
        end

        subgraph KKUAPI ["🔹 KKU AI Gateway"]
            KKURerank(("Gemini\ngemini-3.1-pro-preview\n(Key 2: Rerank)"))
            KKUGen(("Gemini\ngemini-3.1-pro-preview\n(Key 1: LLM)"))
        end
    end

    %% ----------------------------------------------------
    %% Data Flow Connections
    %% ----------------------------------------------------

    %% User to Frontend
    User == "Uses" ==> UI

    %% Frontend to Backends
    UI_Img -- "POST Image\n(VITE_MODEL_URL)" --> API1
    UI_Chat -- "POST Message\n(VITE_CHATBOT_URL)" --> API2

    %% Model Return
    ONNX -. "Return Risk %" .-> UI_Img

    %% RAG Pipeline Flow
    EmbedProcess -- "Request Vector\n[EMBED_API_KEY]" --> GeminiEmbed
    GeminiEmbed -. "Return 768-dim Vector" .-> SearchProcess

    SearchProcess -- "Cosine Similarity Search" --> SupaDB
    SupaDB -. "Return 8 Candidate Docs" .-> RerankProcess

    RerankProcess -- "Send 8 Docs for Scoring\n[RERANK_API_KEY]" --> KKURerank
    KKURerank -. "Return Selected Top 4 Docs" .-> GenProcess

    GenProcess -- "Send System Prompt + Top 4 Docs\n[LLM_API_KEY]" --> KKUGen
    KKUGen -. "Return Final Answer Text" .-> API2

    %% Final Return
    API2 -. "Display Response" .-> UI_Chat

    %% ----------------------------------------------------
    %% Styling
    %% ----------------------------------------------------
    classDef frontend fill:#000000,stroke:#333,stroke-width:2px,color:#fff;
    classDef model fill:#1b4f72,stroke:#2874a6,stroke-width:2px,color:#fff;
    classDef chatbot fill:#145a32,stroke:#1d8348,stroke-width:2px,color:#fff;
    classDef api fill:#b03a2e,stroke:#cb4335,stroke-width:2px,color:#fff;
    classDef db fill:#b7950b,stroke:#d4ac0d,stroke-width:2px,color:#fff;
    classDef process fill:#eaf2f8,stroke:#5dade2,stroke-width:1px,color:#333;

    class UI frontend;
    class API1,ONNX model;
    class API2 chatbot;
    class EmbedProcess,SearchProcess,RerankProcess,GenProcess process;
    class GeminiEmbed,KKURerank,KKUGen api;
    class SupaDB db;
```

---

## 🚀 ข้อดีของสถาปัตยกรรมนี้

1. **แก้ปัญหา RAM บน Free Tier อย่างสมบูรณ์:** ไม่มีการโหลด Model ใดๆ เข้า Memory (ทั้งฝั่ง Computer Vision และ Natural Language) เพราะใช้ ONNX และ External APIs แทน
2. **แม่นยำด้วยการทำ Reranking:** การใช้ LLM มาช่วยวิเคราะห์เอกสารแบบ Re-rank ก่อนจัดเรียง ทำให้ได้ Context ที่เกี่ยวข้องจริงๆ ตัดปัญหาดึงข้อมูลผิดพลาด
3. **ลดค่าใช้จ่ายรัน Server:** เพราะสามารถใช้ระดับ Free Tier ของแพลตฟอร์มต่างๆ รวมกันจนเป็นระบบใหญ่ได้ (Vercel = Host Web, 2x Render = Host 2 APIs, Supabase = DB)
