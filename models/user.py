from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    coins = db.Column(db.Integer, default=100)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    reputation = db.Column(db.Integer, default=0)

    last_gather_time = db.Column(db.DateTime, nullable=True)