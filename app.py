import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from RAG import get_dermatology_response, embed_documents

app = Flask(__name__)
CORS(app)

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
        return jsonify({"reply": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API: Embed ───────────────────────────────────────────────────────────────

@app.route('/api/embed', methods=['POST'])
def embed():
    chunk_size = 500

    # ── Case 1: File upload (multipart/form-data) ──
    if request.files:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "ไม่พบไฟล์ในคำขอ"}), 400

        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ('txt',):
            return jsonify({"error": "รองรับเฉพาะไฟล์ .txt เท่านั้น"}), 400

        chunk_size = int(request.form.get('chunk_size', 500))

        try:
            raw = file.read()
            for encoding in ('utf-8', 'utf-8-sig', 'tis-620', 'cp874', 'latin-1'):
                try:
                    raw_text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                raw_text = raw.decode('utf-8', errors='replace')
        except Exception as e:
            return jsonify({"error": f"ไม่สามารถอ่านไฟล์ได้: {str(e)}"}), 500

    # ── Case 2: JSON body (plain text) ──
    else:
        data = request.get_json(silent=True)
        if not data or not data.get('text', '').strip():
            return jsonify({"error": "ไม่พบข้อความในคำขอ"}), 400

        raw_text = data['text']
        chunk_size = int(data.get('chunk_size', 500))

    # ── Embed ──
    try:
        result = embed_documents(raw_text, chunk_size=chunk_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)