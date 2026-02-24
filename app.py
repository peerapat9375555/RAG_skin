from flask import Flask, render_template, request, jsonify
from RAG import get_dermatology_response, embed_documents
import os

app = Flask(__name__)

# Max upload size: 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# ─── Pages ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/embed')
def embed_page():
    return render_template('embed.html')

# ─── API: Chat ────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        response = get_dermatology_response(user_message)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API: Embed ───────────────────────────────────────────────────────────────

@app.route('/api/embed', methods=['POST'])
def embed():
    chunk_size    = 500
    chunk_overlap = 50

    # ── Case 1: File upload (multipart/form-data) ──
    if request.files:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "ไม่พบไฟล์ในคำขอ"}), 400

        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ('txt', 'docx'):
            return jsonify({"error": "รองรับเฉพาะไฟล์ .txt และ .docx เท่านั้น"}), 400

        chunk_size    = int(request.form.get('chunk_size',    500))
        chunk_overlap = int(request.form.get('chunk_overlap', 50))

        try:
            raw_text = extract_text_from_file(file, ext)
        except Exception as e:
            return jsonify({"error": f"ไม่สามารถอ่านไฟล์ได้: {str(e)}"}), 500

    # ── Case 2: JSON body (plain text) ──
    else:
        data = request.get_json(silent=True)
        if not data or not data.get('text', '').strip():
            return jsonify({"error": "ไม่พบข้อความในคำขอ"}), 400

        raw_text      = data['text']
        chunk_size    = int(data.get('chunk_size',    500))
        chunk_overlap = int(data.get('chunk_overlap', 50))

    # ── Embed ──
    try:
        result = embed_documents(raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_text_from_file(file, ext):
    """Extract plain text from .txt or .docx file object."""
    if ext == 'txt':
        raw = file.read()
        # Try UTF-8, fallback to TIS-620 (Thai encoding)
        for encoding in ('utf-8', 'utf-8-sig', 'tis-620', 'cp874', 'latin-1'):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode('utf-8', errors='replace')

    elif ext == 'docx':
        try:
            import docx
        except ImportError:
            raise RuntimeError(
                "กรุณาติดตั้ง python-docx ก่อน: pip install python-docx"
            )
        import io
        doc = docx.Document(io.BytesIO(file.read()))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n'.join(paragraphs)

    raise ValueError(f"Unsupported extension: {ext}")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
