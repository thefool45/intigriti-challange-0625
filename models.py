from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    instance_id = db.Column(db.String(36), nullable=False, default="default")
    notes = db.relationship('Note', backref='author', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('username', 'instance_id', name='uix_username_instance'),
    )

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    download_link = db.Column(db.String(255), nullable=True)

class Instance(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

