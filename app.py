import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from werkzeug.utils import secure_filename
import uuid
from pymongo import MongoClient # ĐÃ THÊM: Thư viện MongoDB

app = Flask(__name__)
CORS(app)

# Lấy các thông số R2 (Giữ nguyên)
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

# === KẾT NỐI MONGODB ===
MONGO_URI = os.environ.get('MONGO_URI') # Lấy link database từ biến môi trường
client = MongoClient(MONGO_URI)
db = client['truyen_database'] # Tên cơ sở dữ liệu
stories_collection = db['stories'] # Tên bảng (collection) lưu truyện

@app.route('/', methods=['GET'])
def home():
    return "API Server Truyện đang chạy cực êm với MongoDB!", 200

@app.route('/api/upload_comic', methods=['POST'])
def upload_comic():
    try:
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
        
        # ---> LƯU VÀO MONGODB (Thay vì lưu vào biến RAM) <---
        stories_collection.insert_one(new_story)

        # Xóa ID hệ thống của MongoDB trước khi gửi về App để tránh lỗi
        new_story.pop('_id', None)

        return jsonify({"message": "Thành công", "story": new_story}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stories', methods=['GET'])
def get_stories():
    # ---> LẤY DANH SÁCH TỪ MONGODB <---
    # {'_id': 0} giúp ẩn ID của DB đi. .sort('_id', -1) giúp truyện mới nhất luôn nổi lên đầu
    stories = list(stories_collection.find({}, {'_id': 0}).sort('_id', -1))
    return jsonify(stories), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
