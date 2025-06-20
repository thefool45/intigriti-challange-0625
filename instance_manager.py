import os
import uuid
from flask import request, current_app, session
from config import INSTANCES_DIR
from cleanup import update_instance_timestamp

def is_valid_instance_id(instance_id):
    if not instance_id:
        return False
    
    instance_dir = os.path.join(INSTANCES_DIR, instance_id)
    return os.path.exists(instance_dir)

def get_or_create_instance_id():
    if 'instance_id' in session and is_valid_instance_id(session['instance_id']):
        return session['instance_id']
    
    instance_id = request.cookies.get('INSTANCE')
    
    if not is_valid_instance_id(instance_id):
        instance_id = str(uuid.uuid4())
        print(f"Creating new instance: {instance_id}")
    
    instance_dir = os.path.join(INSTANCES_DIR, instance_id)
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        os.makedirs(os.path.join(instance_dir, "notes"), exist_ok=True)
        os.makedirs(os.path.join(instance_dir, "chrome_profile"), exist_ok=True)
    
    update_instance_timestamp(instance_id, app=current_app)
    
    session['instance_id'] = instance_id
    
    return instance_id

def get_instance_path(instance_id, *paths):
    return os.path.join(INSTANCES_DIR, instance_id, *paths)

def set_instance_cookie(response, instance_id):
    if hasattr(response, 'set_cookie'):
        response.set_cookie('INSTANCE', instance_id, max_age=60*60*24*30)
    return response

