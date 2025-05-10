from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80))
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)
