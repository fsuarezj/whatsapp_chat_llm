# tests/test_models.py
import pytest
from src.models.order_model import Order, OrderProduct, OrderType, OrderStatus, db
from src.models.customer_model import Customer
from src.models.product_model import Product

#class DummyCustomer(db.Model):
#    __tablename__ = 'customer'
#    __table_args__ = {'extend_existing': True}
#    id = db.Column(db.Integer, primary_key=True)
#    name = db.Column(db.String(50))
#
#class DummyProduct(db.Model):
#    __tablename__ = 'product'
#    __table_args__ = {'extend_existing': True}
#    id = db.Column(db.Integer, primary_key=True)
#    name = db.Column(db.String(50))

@pytest.fixture(autouse=True)
def setup_dummy_tables(app):
    with app.app_context():
        db.create_all()
        yield
        db.drop_all()

def test_order_customer_relationship(session):
    customer = Customer(name="Alice", phone_number="1234567890")
    session.add(customer)
    session.commit()

    order = Order(
        customer_id=customer.id,
        order_type=OrderType.delivery,
        status=OrderStatus.paid
    )
    session.add(order)
    session.commit()

    assert order.customer == customer
    assert customer.orders[0] == order

def test_order_product_relationship(session):
    customer = Customer(name="Bob", phone_number="1234567890")
    product1 = Product(name="Widget", price=1000)
    product2 = Product(name="Gadget", price=2000)
    session.add_all([customer, product1, product2])
    session.commit()

    order = Order(
        customer_id=customer.id,
        order_type=OrderType.pickup,
        status=OrderStatus.pending
    )
    session.add(order)
    session.commit()

    op1 = OrderProduct(order_id=order.id, product_id=product1.id, quantity=2)
    op2 = OrderProduct(order_id=order.id, product_id=product2.id, quantity=1)
    session.add_all([op1, op2])
    session.commit()

    # Test many-to-many relationship
    assert product1 in order.products
    assert product2 in order.products
    assert order in product1.orders
    assert order in product2.orders

    # Test order_products relationship
    assert len(order.order_products) == 2
    assert order.order_products[0].quantity in [1, 2]

def test_order_fields(session):
    # Create a dummy customer
    customer = DummyCustomer(name="Test Customer")
    session.add(customer)
    session.commit()

    # Create an order with all fields set
    now = datetime.utcnow()
    order = Order(
        customer_id=customer.id,
        order_type=OrderType.delivery,
        status=OrderStatus.paid,
        datetime=now,
        address="123 Test St",
        notes="Leave at the door"
    )
    session.add(order)
    session.commit()

    # Retrieve the order
    retrieved = Order.query.first()

    # Test each field
    assert retrieved.customer_id == customer.id
    assert retrieved.order_type == OrderType.delivery
    assert retrieved.status == OrderStatus.paid
    assert retrieved.datetime == now
    assert retrieved.address == "123 Test St"
    assert retrieved.notes == "Leave at the door"

def test_order_status_default(session):
    customer = DummyCustomer(name="Default Status Customer")
    session.add(customer)
    session.commit()

    order = Order(
        customer_id=customer.id,
        order_type=OrderType.pickup,
        # status not set, should default to pending
    )
    session.add(order)
    session.commit()

    retrieved = Order.query.first()
    assert retrieved.status == OrderStatus.pending