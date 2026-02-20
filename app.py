import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
CORS(app) # Bắt buộc để app Flutter có thể gọi API mà không bị chặn

# Lấy các thông số bảo mật từ Biến Môi Trường (Cài đặt trên Render)
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
    return "API Server Truyện của bạn đang chạy ngon lành!", 200

@app.route('/api/upload_comic', methods=['POST'])
def upload_comic():
    try:
        # Lấy thông tin cơ bản
        title = request.form.get('title', 'Chưa có tên')
        author = request.form.get('author', 'Vô Danh')
        genre = request.form.get('genre', 'Khác')
        
        # ---> LẤY THÊM NỘI DUNG CHỮ VÀ PHÂN LOẠI TRUYỆN <---
        story_type = request.form.get('type', 'comic') # Loại: text, comic, gallery
        content_text = request.form.get('content', '') # Nội dung truyện chữ
        
        folder_id = str(uuid.uuid4())[:8]

        # 1. Upload Cover (Ảnh Bìa - Áp dụng cho mọi loại truyện nếu có)
        cover_file = request.files.get('cover')
        cover_url = ""
        if cover_file:
            filename = secure_filename(cover_file.filename)
            s3_path = f"covers/{folder_id}/cover_{filename}"
            s3.upload_fileobj(cover_file, BUCKET_NAME, s3_path)
            cover_url = f"{PUBLIC_URL}/{s3_path}"

        # 2. Upload Pages (Ảnh truyện tranh / Album)
        pages = request.files.getlist('pages')
        page_urls = []
        
        # Nếu KHÔNG PHẢI là truyện chữ thì mới lưu ảnh pages
        if story_type != 'text':
            for index, page in enumerate(pages):
                page_filename = secure_filename(page.filename)
                # Phân mục thư mục trên R2 cho dễ quản lý
                s3_path = f"{story_type}s/{folder_id}/page_{index}_{page_filename}"
                s3.upload_fileobj(page, BUCKET_NAME, s3_path)
                page_urls.append(f"{PUBLIC_URL}/{s3_path}")

        # 3. Lưu Data vào Database
        new_story = {
            "title": title, 
            "author": author, 
            "genre": genre,
            "type": story_type,       # Đã thêm
            "content": content_text,  # Đã thêm
            "coverUrl": cover_url, 
            "imageUrls": page_urls
        }
        stories_db.insert(0, new_story) # Thêm truyện mới lên đầu danh sách

        return jsonify({"message": "Thành công", "story": new_story}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stories', methods=['GET'])
def get_stories():
    return jsonify(stories_db), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
