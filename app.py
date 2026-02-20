import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
CORS(app) # Bắt buộc để app Flutter có thể gọi API mà không bị chặn

# Lấy các thông số bảo mật từ Biến Môi Trường (Sẽ cài đặt trên Render)
R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
PUBLIC_URL = os.environ.get('R2_PUBLIC_URL')

# Khởi tạo kết nối S3 với Cloudflare R2
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name='auto'
)

# Database tạm thời (lưu trên RAM)
stories_db = []

@app.route('/', methods=['GET'])
def home():
    return "API Server Truyện Tranh đang chạy!", 200

@app.route('/api/upload_comic', methods=['POST'])
def upload_comic():
    try:
        title = request.form.get('title')
        author = request.form.get('author')
        genre = request.form.get('genre')
        folder_id = str(uuid.uuid4())[:8]

        # 1. Upload Cover
        cover_file = request.files.get('cover')
        cover_url = ""
        if cover_file:
            filename = secure_filename(cover_file.filename)
            s3_path = f"comics/{folder_id}/cover_{filename}"
            s3.upload_fileobj(cover_file, BUCKET_NAME, s3_path)
            cover_url = f"{PUBLIC_URL}/{s3_path}"

        # 2. Upload Pages
        pages = request.files.getlist('pages')
        page_urls = []
        for index, page in enumerate(pages):
            page_filename = secure_filename(page.filename)
            s3_path = f"comics/{folder_id}/page_{index}_{page_filename}"
            s3.upload_fileobj(page, BUCKET_NAME, s3_path)
            page_urls.append(f"{PUBLIC_URL}/{s3_path}")

        # 3. Lưu Data
        new_story = {
            "title": title, "author": author, "genre": genre,
            "type": "comic", "coverUrl": cover_url, "imageUrls": page_urls
        }
        stories_db.insert(0, new_story)

        return jsonify({"message": "Thành công", "story": new_story}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stories', methods=['GET'])
def get_stories():
    return jsonify(stories_db), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)