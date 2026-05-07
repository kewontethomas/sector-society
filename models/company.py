from models.user import db


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    name = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    company_type = db.Column(
        db.String(50),
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    reputation = db.Column(
        db.Integer,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )