import os
import re
import time

from flask import render_template, request, jsonify, send_from_directory, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from selenium import webdriver
from sqlalchemy.orm.exc import NoResultFound
from models import db, User, Note
from instance_manager import get_or_create_instance_id, get_instance_path, set_instance_cookie
from utils import sanitize_filename, sanitize_username, get_chrome_options
from selenium.webdriver.chrome.service import Service

def register_routes(app):

    def error_response(message, status_code):
        instance_id = get_or_create_instance_id()
        return set_instance_cookie(
            jsonify({'success': False, 'message': message}),
            instance_id
        ), status_code

    def validate_url(url):
        return url.startswith("http://localhost:1337/")

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html'), 404

    @app.route('/')
    def index():
        instance_id = get_or_create_instance_id()
        response = make_response(render_template('index.html', instance_id=instance_id))
        return set_instance_cookie(response, instance_id)
    
    @app.route('/notes')
    def notes():
        instance_id = get_or_create_instance_id()
        response = make_response(render_template('notes.html', instance_id=instance_id))
        return set_instance_cookie(response, instance_id)

    @app.route('/api/status', methods=['GET'])
    def api_status():
        instance_id = get_or_create_instance_id()
        response_data = {
            'loggedIn': False,
            'instance': instance_id
        }
        
        if current_user.is_authenticated:
            response_data['loggedIn'] = True
            response_data['username'] = current_user.username
        
        response = jsonify(response_data)
        return set_instance_cookie(response, instance_id)

    @app.route('/api/register', methods=['POST'])
    def api_register():
        instance_id = get_or_create_instance_id()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username != sanitize_username(username):
            return error_response("Username contains invalid characters.", 400)
        
        if User.query.filter_by(username=username, instance_id=instance_id).first():
            return error_response("User already exists in this instance", 400)
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, instance_id=instance_id)
        db.session.add(new_user)
        db.session.commit()
        
        return set_instance_cookie(
            jsonify({'success': True, 'message': "Registration successful"}),
            instance_id
        )

    @app.route('/api/login', methods=['POST'])
    def api_login():
        instance_id = get_or_create_instance_id()
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username, instance_id=instance_id).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return set_instance_cookie(
                jsonify({'success': True, 'message': "Login successful"}),
                instance_id
            )
        
        return error_response("Invalid credentials", 401)

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def api_logout():
        instance_id = get_or_create_instance_id()
        logout_user()
        return set_instance_cookie(
            jsonify({'success': True, 'message': "Logout successful"}),
            instance_id
        )

    @app.route('/api/notes', methods=['GET'])
    @login_required
    def get_notes():
        instance_id = get_or_create_instance_id()
        
        db_notes = Note.query.filter_by(user_id=current_user.id).all()
        notes_list = []
        
        for note in db_notes:
            note_data = {'id': note.id, 'content': note.content}
            
            if hasattr(note, 'download_link') and note.download_link:
                note_data['download_link'] = note.download_link
                note_data['filename'] = note.filename
                
            notes_list.append(note_data)

        db_file_names = set()
        pattern = r'/download/[^/]+/([^"]+)'
        for note in db_notes:
            match = re.search(pattern, note.content)
            if match:
                db_file_names.add(match.group(1))
            if hasattr(note, 'filename') and note.filename:
                db_file_names.add(note.filename)

        user_dir = get_instance_path(instance_id, "notes", current_user.username)
        if os.path.exists(user_dir):
            for filename in os.listdir(user_dir):
                if filename in db_file_names:
                    continue
                file_path = os.path.join(user_dir, filename)
                if os.path.isfile(file_path):
                    download_link = f'/download/{current_user.username}/{filename}'
                
                    preview_content = ""
                    try:
                        with open(file_path, 'r', errors='replace') as f:
                            lines = []
                            for i, line in enumerate(f):
                                if i >= 2:
                                    break
                                lines.append(line.strip())
                            preview_content = "\n".join(lines)
                    except Exception as e:
                        preview_content = f"[Preview not available for {filename}]"
                    
                    notes_list.append({
                        'id': None, 
                        'content': preview_content,
                        'download_link': download_link,
                        'filename': filename
                    })
    
        return set_instance_cookie(
            jsonify({'success': True, 'notes': notes_list}),
            instance_id
        )

    @app.route('/api/notes', methods=['POST'])
    @login_required
    def add_note():
        instance_id = get_or_create_instance_id()
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return error_response("Empty content", 400)
        
        note = Note(content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        
        return set_instance_cookie(
            jsonify({'success': True, 'message': "Note added"}),
            instance_id
        )

    @app.route('/api/notes/<int:note_id>', methods=['DELETE'])
    @login_required
    def delete_note(note_id):
        instance_id = get_or_create_instance_id()
        
        try:
            note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
            if not note:
                return error_response("Note not found", 404)

            if hasattr(note, 'filename') and note.filename:
                user_dir = get_instance_path(instance_id, "notes", current_user.username)
                file_path = os.path.join(user_dir, note.filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        return error_response("Error deleting file", 500)
            else:
                pattern = r'/download/[^/]+/([^"]+)'
                match = re.search(pattern, note.content)
                if match:
                    filename = match.group(1)
                    user_dir = get_instance_path(instance_id, "notes", current_user.username)
                    file_path = os.path.join(user_dir, filename)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            return error_response("Error deleting file", 500)

            db.session.delete(note)
            db.session.commit()
            
            return set_instance_cookie(
                jsonify({'success': True, 'message': "Note or file deleted"}),
                instance_id
            )
        except NoResultFound:
            return error_response("Note not found", 404)

    @app.route('/api/notes/upload', methods=['POST'])
    @login_required
    def upload_note():
        instance_id = get_or_create_instance_id()
        
        if 'file' not in request.files:
            return error_response("No file provided", 400)
        
        file = request.files['file']
        if file.filename == '':
            return error_response("No file selected", 400)

        file.seek(0, os.SEEK_END)
        if file.tell() > 20 * 1024:
            return error_response("File size exceeds 20KB limit.", 400)
        file.seek(0)

        notes_dir = get_instance_path(instance_id, "notes")
        os.makedirs(notes_dir, exist_ok=True)
        
        user_dir = os.path.join(notes_dir, current_user.username)
        os.makedirs(user_dir, exist_ok=True)
        
        filename = sanitize_filename(file.filename)
        file_path = os.path.join(user_dir, filename)
        
        try:
            file.save(file_path)
        except Exception:
            return error_response("Error saving file", 500)

        preview_content = ""
        try:
            with open(file_path, 'r', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 2:
                        break
                    lines.append(line.strip())
                preview_content = "\n".join(lines)
        except Exception as e:
            preview_content = f"[Preview not available for {filename}]"
        
        download_link = f'/download/{current_user.username}/{filename}'
        
        note = Note(
            content=preview_content, 
            user_id=current_user.id,
            filename=filename,
            download_link=download_link
        )
        db.session.add(note)
        db.session.commit()
        
        return set_instance_cookie(
            jsonify({'success': True, 'message': "File uploaded successfully"}),
            instance_id
        )

    @app.route('/download/<username>/<path:filename>')
    @login_required
    def download_file(username, filename):
        instance_id = get_or_create_instance_id()
        
        if username != current_user.username:
            return error_response("Unauthorized access", 403)
        
        user_dir = get_instance_path(instance_id, "notes", username)
        response = send_from_directory(user_dir, filename, as_attachment=True)
        return set_instance_cookie(response, instance_id)

    @app.route('/api/visit', methods=['POST'])
    @login_required
    def visit_url():
        instance_id = get_or_create_instance_id()
        data = request.get_json()
        url = data.get('url')
        
        if not validate_url(url):
            return error_response('URL not valid', 400)
        
        response = {
            'success': True, 
            'message': 'URL is valid! Starting the bot...',
            'status': 'url_valid'
        }
        
        try:
            chrome_options = get_chrome_options(instance_id)
            driver = webdriver.Chrome(options=chrome_options, service=Service('/usr/bin/chromedriver'))
            
            driver.get(url)
            time.sleep(15)
            
            driver.quit()
            
            response['message'] = 'Page visited successfully!'
            response['status'] = 'visit_complete'
            
            return set_instance_cookie(jsonify(response), instance_id)
        except Exception as e:
            print(f"Bot error: {str(e)}")
            return error_response('Bot crash...', 500)

