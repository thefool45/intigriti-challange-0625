import os
import time
import shutil
import threading
import logging
from datetime import datetime, timedelta
from config import INSTANCES_DIR
from models import db, Instance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cleanup')

def update_instance_timestamp(instance_id, app=None):
    if not instance_id:
        return
    
    try:
        if app:
            with app.app_context():
                instance = Instance.query.get(instance_id)
                if instance:
                    instance.last_access = datetime.utcnow()
                else:
                    instance = Instance(id=instance_id)
                    db.session.add(instance)
                db.session.commit()
                logger.info(f"Updated timestamp for instance {instance_id}")
        else:
            engine = create_engine(f'sqlite:///{os.path.join(INSTANCES_DIR, "default.db")}')
            Session = sessionmaker(bind=engine)
            session = Session()
            
            instance = session.query(Instance).get(instance_id)
            if instance:
                instance.last_access = datetime.utcnow()
            else:
                instance = Instance(id=instance_id)
                session.add(instance)
            
            session.commit()
            session.close()
            logger.info(f"Updated timestamp for instance {instance_id} (no context)")
    except Exception as e:
        logger.error(f"Error updating timestamp for {instance_id}: {e}")

def cleanup_instances(max_idle_time=900, app=None):
    logger.info(f"Starting instance cleanup (inactivity > {max_idle_time} seconds)...")
    
    current_time = datetime.utcnow()
    cutoff_time = current_time - timedelta(seconds=max_idle_time)
    count_removed = 0
    count_orphaned = 0
    
    try:
        instance_dirs = set()
        for item in os.listdir(INSTANCES_DIR):
            item_path = os.path.join(INSTANCES_DIR, item)
            if os.path.isdir(item_path) and item != "default":
                instance_dirs.add(item)
        
        if app:
            with app.app_context():
                inactive_instances = Instance.query.filter(Instance.last_access < cutoff_time).all()
                
                all_db_instances = set(instance.id for instance in Instance.query.all())
                
                orphaned_instances = instance_dirs - all_db_instances
                
                for instance_id in orphaned_instances:
                    instance_dir = os.path.join(INSTANCES_DIR, instance_id)
                    if os.path.exists(instance_dir):
                        try:
                            logger.info(f"Deleting orphaned instance {instance_id}")
                            shutil.rmtree(instance_dir)
                            count_orphaned += 1
                        except Exception as e:
                            logger.error(f"Error deleting orphaned instance {instance_id}: {e}")
                
                for instance in inactive_instances:
                    instance_dir = os.path.join(INSTANCES_DIR, instance.id)
                    if os.path.exists(instance_dir):
                        try:
                            logger.info(f"Deleting inactive instance {instance.id} (last activity: {instance.last_access})")
                            shutil.rmtree(instance_dir)
                            count_removed += 1
                        except Exception as e:
                            logger.error(f"Error deleting instance {instance.id}: {e}")
                    
                    db.session.delete(instance)
                    logger.info(f"Deleted DB entry for inactive instance {instance.id}")
                
                for instance_id in all_db_instances - instance_dirs:
                    instance = Instance.query.get(instance_id)
                    if instance:
                        logger.info(f"Deleting orphaned DB entry {instance_id}")
                        db.session.delete(instance)
                
                db.session.commit()
        else:
            engine = create_engine(f'sqlite:///{os.path.join(INSTANCES_DIR, "default.db")}')
            Session = sessionmaker(bind=engine)
            session = Session()
            
            inactive_instances = session.query(Instance).filter(Instance.last_access < cutoff_time).all()
            
            all_db_instances = set(instance.id for instance in session.query(Instance).all())
            
            orphaned_instances = instance_dirs - all_db_instances
            
            for instance_id in orphaned_instances:
                instance_dir = os.path.join(INSTANCES_DIR, instance_id)
                if os.path.exists(instance_dir):
                    try:
                        logger.info(f"Deleting orphaned instance {instance_id}")
                        shutil.rmtree(instance_dir)
                        count_orphaned += 1
                    except Exception as e:
                        logger.error(f"Error deleting orphaned instance {instance_id}: {e}")
            
            for instance in inactive_instances:
                instance_dir = os.path.join(INSTANCES_DIR, instance.id)
                if os.path.exists(instance_dir):
                    try:
                        logger.info(f"Deleting inactive instance {instance.id} (last activity: {instance.last_access})")
                        shutil.rmtree(instance_dir)
                        count_removed += 1
                    except Exception as e:
                        logger.error(f"Error deleting instance {instance.id}: {e}")
                
                session.delete(instance)
                logger.info(f"Deleted DB entry for inactive instance {instance.id}")
            
            for instance_id in all_db_instances - instance_dirs:
                instance = session.query(Instance).get(instance_id)
                if instance:
                    logger.info(f"Deleting orphaned DB entry {instance_id}")
                    session.delete(instance)
            
            session.commit()
            session.close()
    except Exception as e:
        logger.error(f"Error during instance cleanup: {e}")
    
    logger.info(f"Cleanup complete. {count_removed} inactive instances and {count_orphaned} orphaned instances deleted.")

def start_cleanup_thread(app, interval=300):
    def cleanup_worker():
        while True:
            try:
                cleanup_instances(app=app)
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
            
            time.sleep(interval)
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info(f"Cleanup thread started (interval: {interval} seconds, inactivity timeout: 15 minutes)")
    
    return cleanup_thread

def verify_cleanup_system():
    logger.info("Verifying cleanup system...")
    
    if not os.path.exists(INSTANCES_DIR):
        logger.error(f"Instances directory does not exist: {INSTANCES_DIR}")
        return False
    
    default_db_path = os.path.join(INSTANCES_DIR, "default.db")
    if not os.path.exists(default_db_path):
        logger.warning(f"Default database does not exist: {default_db_path}")
    
    try:
        instance_dirs = set()
        for item in os.listdir(INSTANCES_DIR):
            item_path = os.path.join(INSTANCES_DIR, item)
            if os.path.isdir(item_path) and item != "default":
                instance_dirs.add(item)
        
        engine = create_engine(f'sqlite:///{default_db_path}')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        db_instances = set()
        try:
            db_instances = set(instance.id for instance in session.query(Instance).all())
        except Exception as e:
            logger.error(f"Error retrieving instances from DB: {e}")
        
        session.close()
        
        orphaned_dirs = instance_dirs - db_instances
        orphaned_db_entries = db_instances - instance_dirs
        
        if orphaned_dirs:
            logger.warning(f"Instance directories without DB entry: {orphaned_dirs}")
        
        if orphaned_db_entries:
            logger.warning(f"DB entries without instance directory: {orphaned_db_entries}")
        
        logger.info(f"Verification complete. {len(instance_dirs)} instance directories, {len(db_instances)} DB entries.")
        return True
    except Exception as e:
        logger.error(f"Error verifying cleanup system: {e}")
        return False

def test_cleanup_system(debug=False):
    return False
