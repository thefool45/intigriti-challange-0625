from flask import Flask, request, session
from flask_login import LoginManager, logout_user
from models import db, User, Instance
from config import SECRET_KEY, SQLALCHEMY_TRACK_MODIFICATIONS, INSTANCES_DIR
import os
from routes import register_routes  
from instance_manager import get_or_create_instance_id, get_instance_path, is_valid_instance_id
from cleanup import start_cleanup_thread, verify_cleanup_system
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

default_db_path = os.path.join(INSTANCES_DIR, "default.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{default_db_path}'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

db.init_app(app)

def check_and_update_schema(db_path):
    if not os.path.exists(db_path):
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'instance_id' not in columns:
            instance_id = os.path.basename(os.path.dirname(db_path))
            
            try:
                cursor.execute("ALTER TABLE user ADD COLUMN instance_id VARCHAR(36)")
                cursor.execute("UPDATE user SET instance_id = ?", (instance_id,))
                conn.commit()
                print(f"Added instance_id column to user table for instance {instance_id}")
            except sqlite3.OperationalError:
                cursor.execute("SELECT id, username, password FROM user")
                users = cursor.fetchall()
                
                cursor.execute("CREATE TABLE user_temp (id INTEGER PRIMARY KEY, username VARCHAR(150) NOT NULL, password VARCHAR(150) NOT NULL, instance_id VARCHAR(36) NOT NULL)")
                
                for user_id, username, password in users:
                    cursor.execute("INSERT INTO user_temp (id, username, password, instance_id) VALUES (?, ?, ?, ?)", 
                                  (user_id, username, password, instance_id))
                
                cursor.execute("DROP TABLE user")
                cursor.execute("ALTER TABLE user_temp RENAME TO user")
                conn.commit()
                print(f"Recreated user table with instance_id for instance {instance_id}")
    
    conn.close()

@login_manager.user_loader
def load_user(user_id):
    current_instance = session.get('instance_id')
    
    if not current_instance or current_instance != request.cookies.get('INSTANCE'):
        return None
    
    try:
        user = User.query.filter_by(id=int(user_id)).first()
        
        if user and hasattr(user, 'instance_id') and user.instance_id != current_instance:
            return None
        
        return user
    except Exception as e:
        print(f"Error loading user: {e}")
        logout_user()
        return None

@app.before_request
def before_request():
    if request.endpoint != 'static':
        instance_id = get_or_create_instance_id()
        
        previous_instance = session.get('instance_id')
        
        if previous_instance and previous_instance != instance_id:
            logout_user()
        
        db_path = get_instance_path(instance_id, "app.db")
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        
        check_and_update_schema(db_path)
        
        with app.app_context():
            db.create_all()


register_routes(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    verify_cleanup_system()
    
    cleanup_thread = start_cleanup_thread(app, interval=300)
    
    app.run(debug=False, host='0.0.0.0', port=1337)
