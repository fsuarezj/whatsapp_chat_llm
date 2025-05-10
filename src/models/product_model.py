from .user_model import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    picture_url = db.Column(db.String(255))
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    
    # Add these relationships
    orders = db.relationship('Order', secondary='order_product', back_populates='products', overlaps="order_products")
    order_products = db.relationship('OrderProduct', back_populates='product', overlaps="orders,products")
