import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from werkzeug.utils import secure_filename
import uuid
from pymongo import MongoClient
import certifi

# Khởi tạo chứng chỉ SSL cho MongoDB
ca = certifi.where()

app = Flask(__name__)
CORS(app)

# 1. Cấu hình R2
R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
PUBLIC_URL = os.environ.get('R2_PUBLIC_URL')

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name='auto'
)

# 2. Kết nối MongoDB
MONGO_URI = os.environ.get('MONGO_URI')

try:
    # Kết nối theo chuẩn đơn giản để tránh lỗi SSL Handshake
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        tlsAllowInvalidCertificates=True
    )
    # Lấy database mặc định từ URI
    db = client.get_database() 
    stories_collection = db['stories']
    
    # Kiểm tra thực tế
    client.admin.command('ping')
    print("✅ KẾT NỐI MONGODB THÀNH CÔNG!")
except Exception as e:
    print(f"❌ LỖI KẾT NỐI MONGODB: {e}")
    stories_collection = None

@app.route('/', methods=['GET'])
def home():
    return "API Server Truyện đang chạy cực êm với MongoDB!", 200

@app.route('/api/upload_comic', methods=['POST'])
def upload_comic():
    try:
        if stories_collection is None:
            return jsonify({"error": "Database chưa kết nối thành công"}), 500

        title = request.form.get('title', 'Chưa có tên')
        author = request.form.get('author', 'Vô Danh')
        genre = request.form.get('genre', 'Khác')
        story_type = request.form.get('type', 'comic')
        content_text = request.form.get('content', '')
        
        folder_id = str(uuid.uuid4())[:8]

        cover_file = request.files.get('cover')
        cover_url = ""
        if cover_file:
            filename = secure_filename(cover_file.filename)
            s3_path = f"covers/{folder_id}/cover_{filename}"
            s3.upload_fileobj(cover_file, BUCKET_NAME, s3_path)
            cover_url = f"{PUBLIC_URL}/{s3_path}"

        pages = request.files.getlist('pages')
        page_urls = []
        if story_type != 'text':
            for index, page in enumerate(pages):
                page_filename = secure_filename(page.filename)
                s3_path = f"{story_type}s/{folder_id}/page_{index}_{page_filename}"
                s3.upload_fileobj(page, BUCKET_NAME, s3_path)
                page_urls.append(f"{PUBLIC_URL}/{s3_path}")

        new_story = {
            "title": title, 
            "author": author, 
            "genre": genre,
            "type": story_type,
            "content": content_text,
            "coverUrl": cover_url, 
            "imageUrls": page_urls
        }
        
        stories_collection.insert_one(new_story)
        new_story.pop('_id', None)

        return jsonify({"message": "Thành công", "story": new_story}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stories', methods=['GET'])
def get_stories():
    try:
        if stories_collection is None:
            return jsonify([]), 200
        stories = list(stories_collection.find({}, {'_id': 0}).sort('_id', -1))
        return jsonify(stories), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
