from . import db
from sqlalchemy import Enum
import enum
from datetime import datetime

class OrderType(enum.Enum):
    delivery = "delivery"
    pickup = "pickup"

class OrderPaymentStatus(enum.Enum):
    paid = "paid"
    notPaid = "notPaid"

class OrderDeliveryStatus(enum.Enum):
    delivered = "delivered"
    notDelivered = "notDelivered"

class OrderProduct(db.Model):
    __tablename__ = 'order_product'
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    
    order = db.relationship('Order', back_populates='order_products', overlaps="products,orders")
    product = db.relationship('Product', back_populates='order_products', overlaps="orders,products")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))
    
    products = db.relationship('Product', secondary='order_product', back_populates='orders', overlaps="order_products")
    order_type = db.Column(Enum(OrderType), nullable=False)
    payment_status = db.Column(Enum(OrderPaymentStatus), nullable=False, default=OrderPaymentStatus.notPaid)
    delivery_status = db.Column(Enum(OrderDeliveryStatus), nullable=False, default=OrderDeliveryStatus.notDelivered)
    datetime = db.Column(db.DateTime)
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)
    @property
    def total_amount(self):
        return sum(product.price * order_product.quantity for product, order_product in zip(self.products, self.order_products))
    
    order_products = db.relationship('OrderProduct', back_populates='order', overlaps="products,orders")
