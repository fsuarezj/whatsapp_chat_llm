from flask import Blueprint, request, jsonify
from models import db
from models.order_model import Order, OrderProduct, OrderType, OrderPaymentStatus, OrderDeliveryStatus
from models.customer_model import Customer
from models.product_model import Product
from decorators import jwt_required
from werkzeug.exceptions import BadRequest, NotFound
import datetime
from sqlalchemy import and_, select

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders', methods=['GET', 'POST'])
@jwt_required
def orders(user_id):
    if request.method == 'POST':
        data = request.json
        validate_order_data(data)
        
        # Check for duplicate order
        if is_duplicate_order(data):
            raise BadRequest('Duplicate order detected')
            
        # Create order
        order = Order(
            customer_id=data['customer_id'],
            order_type=OrderType(data['order_type']),
            datetime=datetime.datetime.fromisoformat(data.get('datetime', datetime.datetime.now(datetime.UTC).isoformat())),
            payment_status=OrderPaymentStatus.not_paid,
            delivery_status=OrderDeliveryStatus.not_delivered
        )
        db.session.add(order)
        db.session.flush()  # Get order ID without committing
        
        # Add order items
        for item in data['items']:
            validate_order_item(item)
            order_product = OrderProduct(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity']
            )
            db.session.add(order_product)
        
        db.session.commit()
        return jsonify({
            'id': order.id,
            'customer_id': order.customer_id,
            'order_type': order.order_type.value,
            'payment_status': order.payment_status.value,
            'delivery_status': order.delivery_status.value,
            'datetime': order.datetime.isoformat(),
            'total_amount': order.total_amount
        }), 201
    else:
        # Handle GET request with filters
        query = select(Order)
        
        # Filter by date if provided
        date_str = request.args.get('date')
        if date_str:
            try:
                filter_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Order.datetime) == filter_date)
            except ValueError:
                raise BadRequest('Invalid date format. Use YYYY-MM-DD')
        
        # Filter by customer if provided
        customer_id = request.args.get('customer_id')
        if customer_id:
            try:
                customer_id = int(customer_id)
                query = query.filter(Order.customer_id == customer_id)
            except ValueError:
                raise BadRequest('Invalid customer ID')
        
        orders = db.session.execute(query).scalars().all()
        return jsonify([format_order(order) for order in orders]), 200

@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required
def get_order(order_id, user_id):
    order = db.session.get(Order, order_id)
    if not order:
        raise NotFound('Order not found')
    return jsonify(format_order(order)), 200

@orders_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required
def update_order_status(order_id, user_id):
    order = db.session.get(Order, order_id)
    if not order:
        raise NotFound('Order not found')
    
    data = request.json
    
    if not isinstance(data, dict):
        raise BadRequest('Invalid data format')
    
    if 'payment_status' in data:
        try:
            order.payment_status = OrderPaymentStatus(data['payment_status'])
        except ValueError:
            raise BadRequest('Invalid payment status')
    
    if 'delivery_status' in data:
        try:
            order.delivery_status = OrderDeliveryStatus(data['delivery_status'])
        except ValueError:
            raise BadRequest('Invalid delivery status')
    
    db.session.commit()
    return jsonify({'message': 'Order status updated successfully'}), 200

@orders_bp.route('/orders/<int:order_id>', methods=['DELETE'])
@jwt_required
def delete_order(order_id, user_id):
    order = db.session.get(Order, order_id)
    if not order:
        raise NotFound('Order not found')
    
    if order.payment_status == OrderPaymentStatus.paid or order.delivery_status == OrderDeliveryStatus.delivered:
        raise BadRequest('Cannot delete paid or delivered orders')
    
    # Delete all entries in order_product for this order
    db.session.query(OrderProduct).filter_by(order_id=order.id).delete()
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': 'Order deleted successfully'}), 200

def validate_order_data(data):
    if not isinstance(data, dict):
        raise BadRequest('Invalid data format')
    
    required_fields = {'customer_id', 'order_type', 'items'}
    missing_fields = required_fields - set(data.keys())
    if missing_fields:
        raise BadRequest(f'Missing required fields: {", ".join(missing_fields)}')
    
    # Validate customer exists
    customer = db.session.get(Customer, data['customer_id'])
    if not customer:
        raise BadRequest('Customer not found')
    
    # Validate order type
    try:
        OrderType(data['order_type'])
    except ValueError:
        raise BadRequest('Invalid order type')
    
    # Validate items
    if not isinstance(data['items'], list) or not data['items']:
        raise BadRequest('Order must contain at least one item')
    
    for item in data['items']:
        validate_order_item(item)

def validate_order_item(item):
    if not isinstance(item, dict):
        raise BadRequest('Invalid item format')
    
    required_fields = {'product_id', 'quantity'}
    missing_fields = required_fields - set(item.keys())
    if missing_fields:
        raise BadRequest(f'Missing required fields in item: {", ".join(missing_fields)}')
    
    # Validate product exists
    product = db.session.get(Product, item['product_id'])
    if not product:
        raise BadRequest(f'Product with ID {item["product_id"]} not found')
    
    # Validate quantity
    try:
        quantity = int(item['quantity'])
        if quantity <= 0:
            raise ValueError
    except ValueError:
        raise BadRequest('Quantity must be a positive integer')

def is_duplicate_order(data):
    # Check if there's an identical order in the last hour
    query = select(Order).filter(
        and_(
            Order.customer_id == data['customer_id'],
            Order.datetime >= datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        )
    )
    recent_orders = db.session.execute(query).scalars().all()
    
    for order in recent_orders:
        if len(order.order_products) != len(data['items']):
            continue
        
        # Check if all items match
        order_items = {(op.product_id, op.quantity) for op in order.order_products}
        new_items = {(item['product_id'], item['quantity']) for item in data['items']}
        
        if order_items == new_items:
            return True
    
    return False

def format_order(order):
    return {
        'id': order.id,
        'customer_id': order.customer_id,
        'order_type': order.order_type.value,
        'payment_status': order.payment_status.value,
        'delivery_status': order.delivery_status.value,
        'datetime': order.datetime.isoformat(),
        'items': [
            {
                'product_id': op.product_id,
                'quantity': op.quantity,
                'price': op.product.price
            }
            for op in order.order_products
        ],
        'total_amount': order.total_amount
    } 