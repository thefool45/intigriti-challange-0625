import os

INSTANCES_DIR = os.path.join(os.getcwd(), "instances")
os.makedirs(INSTANCES_DIR, exist_ok=True)

SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24).hex())

SQLALCHEMY_TRACK_MODIFICATIONS = False

