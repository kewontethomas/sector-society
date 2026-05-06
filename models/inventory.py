from models.user import db

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    resource_name = db.Column(db.String(50), nullable=False)

    quantity = db.Column(db.Integer, default=0)