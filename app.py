import os
import sqlite3
import uuid
import hashlib
import secrets
import qrcode
import zipfile
import io
import csv
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    send_file, abort, redirect
)
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

MAX_IMAGE_SIZE = 1280
IMAGE_QUALITY = 70
STORAGE_WARN_MB = 400
STORAGE_LIMIT_MB = 512

IS_CLOUD = os.environ.get('PYTHONANYWHERE') == '1' or os.path.exists('/home')

if IS_CLOUD:
    USER = os.environ.get('USER', 'safety')
    BASE_DIR = f'/home/{USER}/safety_platform'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, 'data', 'issues.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
QR_FOLDER = os.path.join(BASE_DIR, 'qrcodes')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT NOT NULL,
            reporter TEXT,
            phone TEXT,
            status TEXT DEFAULT '待处理',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_image(filepath):
    try:
        img = Image.open(filepath)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        w, h = img.size
        if max(w, h) > MAX_IMAGE_SIZE:
            ratio = MAX_IMAGE_SIZE / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(filepath, 'JPEG', quality=IMAGE_QUALITY, optimize=True)
        return True
    except Exception:
        return False


def save_photos(files, issue_id):
    saved = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            new_name = f'issue_{issue_id}_{uuid.uuid4().hex[:8]}.jpg'
            filepath = os.path.join(UPLOAD_FOLDER, new_name)
            file.save(filepath)
            compress_image(filepath)
            saved.append(new_name)
    return saved


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return redirect('/admin')


@app.route('/submit', methods=['POST'])
def submit_issue():
    data = request.form
    location = data.get('location', '').strip()
    issue_type = data.get('issue_type', '').strip()
    description = data.get('description', '').strip()
    reporter = data.get('reporter', '').strip()
    phone = data.get('phone', '').strip()

    if not location or not issue_type or not description:
        return jsonify({'success': False, 'message': '请填写所有必填项'}), 400

    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO issues (location, issue_type, description, reporter, phone) VALUES (?, ?, ?, ?, ?)',
        (location, issue_type, description, reporter, phone)
    )
    issue_id = cursor.lastrowid

    photos = request.files.getlist('photos')
    saved_photos = save_photos(photos, issue_id)

    for filename in saved_photos:
        conn.execute(
            'INSERT INTO photos (issue_id, filename) VALUES (?, ?)',
            (issue_id, filename)
        )

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '隐患上报成功，感谢您的贡献！'})


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/api/issues')
def get_issues():
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    conn = get_db()
    query = 'SELECT * FROM issues WHERE 1=1'
    params = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    if keyword:
        query += ' AND (location LIKE ? OR description LIKE ? OR reporter LIKE ?)'
        kw = f'%{keyword}%'
        params.extend([kw, kw, kw])
    query += ' ORDER BY created_at DESC'
    rows = conn.execute(query, params).fetchall()
    issues = []
    for row in rows:
        issue = dict(row)
        photos = conn.execute(
            'SELECT filename FROM photos WHERE issue_id = ?', (issue['id'],)
        ).fetchall()
        issue['photos'] = [p['filename'] for p in photos]
        issues.append(issue)
    conn.close()
    return jsonify(issues)


@app.route('/api/issues/<int:issue_id>', methods=['POST'])
def update_issue(issue_id):
    status = request.json.get('status', '')
    if status not in ('待处理', '处理中', '已处理', '已关闭'):
        return jsonify({'success': False, 'message': '无效的状态'}), 400
    conn = get_db()
    conn.execute('UPDATE issues SET status = ? WHERE id = ?', (status, issue_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/issues/<int:issue_id>', methods=['DELETE'])
def delete_issue(issue_id):
    conn = get_db()
    photos = conn.execute(
        'SELECT filename FROM photos WHERE issue_id = ?', (issue_id,)
    ).fetchall()
    for photo in photos:
        filepath = os.path.join(UPLOAD_FOLDER, photo['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
    conn.execute('DELETE FROM photos WHERE issue_id = ?', (issue_id,))
    conn.execute('DELETE FROM issues WHERE id = ?', (issue_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/qrcode')
def qr_page():
    return render_template('qrcode.html')


@app.route('/api/generate_qrcode')
def generate_qrcode():
    base_url = request.url_root.rstrip('/')
    url = f'{base_url}/'
    img = qrcode.make(url)
    filename = f'safety_qrcode_{datetime.now().strftime("%Y%m%d")}.png'
    filepath = os.path.join(QR_FOLDER, filename)
    img.save(filepath)
    return jsonify({
        'success': True,
        'url': url,
        'qrcode_path': f'/qrcodes/{filename}'
    })


@app.route('/qrcodes/<filename>')
def serve_qrcode(filename):
    return send_from_directory(QR_FOLDER, filename)


def get_storage_usage():
    total = 0
    counts = {'photos': 0, 'db': 0, 'other': 0}
    for dirpath, dirnames, filenames in os.walk(BASE_DIR):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if os.path.isfile(fp):
                size = os.path.getsize(fp)
                total += size
                if dirpath == UPLOAD_FOLDER:
                    counts['photos'] += 1
                elif dirpath == os.path.join(BASE_DIR, 'data'):
                    counts['db'] += 1
                else:
                    counts['other'] += 1
    return {
        'total_mb': round(total / (1024 * 1024), 2),
        'counts': counts,
        'percent': round(total / (STORAGE_LIMIT_MB * 1024 * 1024) * 100, 1),
        'warn': total >= STORAGE_WARN_MB * 1024 * 1024,
        'critical': total >= STORAGE_LIMIT_MB * 1024 * 1024
    }


@app.route('/api/storage')
def storage_info():
    return jsonify(get_storage_usage())


@app.route('/api/archive')
def archive_all():
    conn = get_db()
    rows = conn.execute('SELECT * FROM issues ORDER BY id').fetchall()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(['ID', '位置', '隐患类型', '描述', '上报人', '电话', '状态', '上报时间', '照片文件名'])
        for row in rows:
            issue = dict(row)
            photos = conn.execute(
                'SELECT filename FROM photos WHERE issue_id = ?', (issue['id'],)
            ).fetchall()
            photo_names = '; '.join(p['filename'] for p in photos)
            writer.writerow([
                issue['id'], issue['location'], issue['issue_type'],
                issue['description'], issue['reporter'], issue['phone'],
                issue['status'], issue['created_at'], photo_names
            ])
        zf.writestr('safety_issues.csv', csv_data.getvalue())

        for photo in conn.execute('SELECT filename FROM photos').fetchall():
            fp = os.path.join(UPLOAD_FOLDER, photo['filename'])
            if os.path.exists(fp):
                zf.write(fp, os.path.join('photos', photo['filename']))

        zf.writestr('archive_info.txt',
            f'归档时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'隐患总数: {len(rows)}\n'
            f'存储大小: {get_storage_usage()["total_mb"]} MB\n'
        )
    conn.close()

    buf.seek(0)
    filename = f'safety_archive_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/clean', methods=['POST'])
def clean_old():
    days = request.json.get('days', 30)
    status = request.json.get('status', '')

    conn = get_db()
    query = "SELECT id FROM issues WHERE created_at < datetime('now', ?)"
    params = [f'-{days} days']
    if status:
        query += " AND status = ?"
        params.append(status)
    issue_ids = [r['id'] for r in conn.execute(query, params).fetchall()]

    deleted_photos = 0
    for iid in issue_ids:
        photos = conn.execute(
            'SELECT filename FROM photos WHERE issue_id = ?', (iid,)
        ).fetchall()
        for photo in photos:
            fp = os.path.join(UPLOAD_FOLDER, photo['filename'])
            if os.path.exists(fp):
                os.remove(fp)
                deleted_photos += 1
        conn.execute('DELETE FROM photos WHERE issue_id = ?', (iid,))
        conn.execute('DELETE FROM issues WHERE id = ?', (iid,))

    conn.commit()
    remaining = conn.execute('SELECT COUNT(*) as cnt FROM issues').fetchone()['cnt']
    conn.close()

    return jsonify({
        'success': True,
        'deleted_issues': len(issue_ids),
        'deleted_photos': deleted_photos,
        'remaining': remaining,
        'storage': get_storage_usage()
    })


@app.route('/api/clean_all_photos', methods=['POST'])
def clean_all_photos():
    conn = get_db()
    photos = conn.execute('SELECT filename FROM photos').fetchall()
    deleted = 0
    for photo in photos:
        fp = os.path.join(UPLOAD_FOLDER, photo['filename'])
        if os.path.exists(fp):
            os.remove(fp)
            deleted += 1
    conn.execute('DELETE FROM photos')
    conn.commit()
    conn.close()
    return jsonify({
        'success': True,
        'deleted_photos': deleted,
        'storage': get_storage_usage()
    })


@app.route('/api/export')
def export_issues():
    conn = get_db()
    rows = conn.execute('SELECT * FROM issues ORDER BY created_at DESC').fetchall()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow([
            'ID', '位置', '隐患类型', '描述', '上报人', '电话',
            '状态', '上报时间', '照片数', '照片文件名'
        ])
        for row in rows:
            issue = dict(row)
            photos = conn.execute(
                'SELECT filename FROM photos WHERE issue_id = ? ORDER BY id', (issue['id'],)
            ).fetchall()
            photo_names = []
            for idx, photo in enumerate(photos, 1):
                src = os.path.join(UPLOAD_FOLDER, photo['filename'])
                if os.path.exists(src):
                    safe_loc = issue['location'].replace('/', '_').replace('\\', '_')[:20]
                    new_name = f'隐患{issue["id"]}_{idx}_{safe_loc}.jpg'
                    zf.write(src, os.path.join('photos', new_name))
                    photo_names.append(new_name)
            writer.writerow([
                issue['id'], issue['location'], issue['issue_type'],
                issue['description'], issue['reporter'], issue['phone'],
                issue['status'], issue['created_at'],
                len(photo_names), '; '.join(photo_names)
            ])
        zf.writestr('隐患记录.csv', csv_data.getvalue().encode('utf-8-sig'))
        zf.writestr('说明.txt',
            f'导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'隐患总数: {len(rows)}\n\n'
            f'文件说明:\n'
            f'  隐患记录.csv - 所有隐患数据（含照片文件名列）\n'
            f'  photos/ 文件夹 - 现场照片\n\n'
            f'照片命名规则: 隐患{chr(123)}ID{chr(125)}_{chr(123)}序号{chr(125)}_{chr(123)}位置{chr(125)}.jpg\n'
            f'  例如: 隐患3_1_信号楼.jpg 表示第3条隐患的第1张照片，位置在信号楼\n'
        )
    conn.close()

    buf.seek(0)
    filename = f'隐患数据导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), path)


init_db()

if __name__ == '__main__':
    if IS_CLOUD:
        app.run(host='0.0.0.0', port=80, debug=False)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
