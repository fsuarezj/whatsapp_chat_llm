from flask_restx import Namespace, Resource, fields
from flask import request
from models import db
from models.order_model import Order, OrderProduct, OrderType, OrderPaymentStatus, OrderDeliveryStatus
from models.customer_model import Customer
from models.product_model import Product
from decorators import jwt_required
from werkzeug.exceptions import BadRequest, NotFound
import datetime
from sqlalchemy import and_, select

# Create namespace
api = Namespace('orders', description='Order operations')

# Define models for Swagger documentation
order_item_model = api.model('OrderItem', {
    'product_id': fields.Integer(required=True, description='ID of the product'),
    'quantity': fields.Integer(required=True, description='Quantity of the product', min=1)
})

order_model = api.model('Order', {
    'id': fields.Integer(readonly=True, description='Order ID'),
    'customer_id': fields.Integer(required=True, description='ID of the customer'),
    'order_type': fields.String(required=True, description='Type of order (pickup or delivery)', enum=['pickup', 'delivery']),
    'payment_status': fields.String(description='Payment status', enum=['notPaid', 'paid']),
    'delivery_status': fields.String(description='Delivery status', enum=['notDelivered', 'delivered']),
    'datetime': fields.DateTime(description='Order datetime'),
    'items': fields.List(fields.Nested(order_item_model), required=True, description='List of items in the order'),
    'total_amount': fields.Float(description='Total order amount')
})

@api.route('/orders')
class OrderList(Resource):
    @api.doc('list_orders', security='bearerAuth')
    @api.marshal_list_with(order_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(400, 'Invalid query parameters')
    @jwt_required
    def get(self, user_id):
        """List all orders with optional filters"""
        query = select(Order)
        
        date_str = request.args.get('date')
        if date_str:
            try:
                filter_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Order.datetime) == filter_date)
            except ValueError:
                api.abort(400, 'Invalid date format. Use YYYY-MM-DD')
        
        customer_id = request.args.get('customer_id')
        if customer_id:
            try:
                customer_id = int(customer_id)
                query = query.filter(Order.customer_id == customer_id)
            except ValueError:
                api.abort(400, 'Invalid customer ID')
        
        orders = db.session.execute(query).scalars().all()
        return [format_order(order) for order in orders]

    @api.doc('create_order', security='bearerAuth')
    @api.expect(order_model)
    @api.marshal_with(order_model, code=201)
    @api.response(201, 'Order created successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(409, 'Duplicate order detected')
    @jwt_required
    def post(self, user_id):
        """Create a new order"""
        data = api.payload
        validate_order_data(data)
        
        if is_duplicate_order(data):
            api.abort(400, 'Duplicate order detected')
            
        order = Order(
            customer_id=data['customer_id'],
            order_type=OrderType(data['order_type']),
            datetime=datetime.datetime.fromisoformat(data.get('datetime', datetime.datetime.now(datetime.UTC).isoformat())),
            payment_status=OrderPaymentStatus.notPaid,
            delivery_status=OrderDeliveryStatus.notDelivered
        )
        db.session.add(order)
        db.session.flush()
        
        for item in data['items']:
            validate_order_item(item)
            order_product = OrderProduct(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity']
            )
            db.session.add(order_product)
        
        db.session.commit()
        return format_order(order), 201

@api.route('/orders/<int:order_id>')
@api.param('order_id', 'The order identifier')
class OrderResource(Resource):
    @api.doc('get_order', security='bearerAuth')
    @api.marshal_with(order_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Order not found')
    @jwt_required
    def get(self, order_id, user_id):
        """Get an order by ID"""
        order = db.session.get(Order, order_id)
        if not order:
            api.abort(404, 'Order not found')
        return format_order(order)

    @api.doc('delete_order', security='bearerAuth')
    @api.response(204, 'Order deleted successfully')
    @api.response(400, 'Cannot delete paid or delivered orders')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Order not found')
    @jwt_required
    def delete(self, order_id, user_id):
        """Delete an order"""
        order = db.session.get(Order, order_id)
        if not order:
            api.abort(404, 'Order not found')
        
        if order.payment_status == OrderPaymentStatus.paid or order.delivery_status == OrderDeliveryStatus.delivered:
            api.abort(400, 'Cannot delete paid or delivered orders')
        
        db.session.query(OrderProduct).filter_by(order_id=order.id).delete()
        db.session.delete(order)
        db.session.commit()
        return '', 204

@api.route('/orders/<int:order_id>/payment_status')
@api.param('order_id', 'The order identifier')
class OrderPaymentStatusResource(Resource):
    @api.doc('update_order_payment_status', security='bearerAuth')
    @api.expect(api.model('OrderPaymentStatus', {
        'payment_status': fields.String(enum=['notPaid', 'paid'])
    }))
    @api.response(200, 'Order payment status updated successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Order not found')
    @jwt_required
    def put(self, order_id, user_id):
        """Update order payment status"""
        order = db.session.get(Order, order_id)
        if not order:
            api.abort(404, 'Order not found')
        
        data = api.payload
        if not isinstance(data, dict):
            api.abort(400, 'Invalid data format')
        
        if 'payment_status' not in data:
            api.abort(400, 'payment_status is required')
        
        try:
            order.payment_status = OrderPaymentStatus(data['payment_status'])
        except ValueError:
            api.abort(400, 'Invalid payment status')
        
        db.session.commit()
        return {'message': 'Order payment status updated successfully'}, 200

@api.route('/orders/<int:order_id>/delivery_status')
@api.param('order_id', 'The order identifier')
class OrderDeliveryStatusResource(Resource):
    @api.doc('update_order_delivery_status', security='bearerAuth')
    @api.expect(api.model('OrderDeliveryStatus', {
        'delivery_status': fields.String(enum=['notDelivered', 'delivered'])
    }))
    @api.response(200, 'Order delivery status updated successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Order not found')
    @jwt_required
    def put(self, order_id, user_id):
        """Update order delivery status"""
        order = db.session.get(Order, order_id)
        if not order:
            api.abort(404, 'Order not found')
        
        data = api.payload
        if not isinstance(data, dict):
            api.abort(400, 'Invalid data format')
        
        if 'delivery_status' not in data:
            api.abort(400, 'delivery_status is required')
        
        try:
            order.delivery_status = OrderDeliveryStatus(data['delivery_status'])
        except ValueError:
            api.abort(400, 'Invalid delivery status')
        
        db.session.commit()
        return {'message': 'Order delivery status updated successfully'}, 200

@api.route('/orders/<int:order_id>/order_type')
@api.param('order_id', 'The order identifier')
class OrderTypeResource(Resource):
    @api.doc('update_order_type', security='bearerAuth')
    @api.expect(api.model('OrderType', {
        'order_type': fields.String(enum=['pickup', 'delivery'])
    }))
    @api.response(200, 'Order type updated successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Order not found')
    @jwt_required
    def put(self, order_id, user_id):
        """Update order type"""
        order = db.session.get(Order, order_id)
        if not order:
            api.abort(404, 'Order not found')
        
        data = api.payload
        if not isinstance(data, dict):
            api.abort(400, 'Invalid data format')
        
        if 'order_type' not in data:
            api.abort(400, 'order_type is required')
        
        try:
            order.order_type = OrderType(data['order_type'])
        except ValueError:
            api.abort(400, 'Invalid order type')
        
        db.session.commit()
        return {'message': 'Order type updated successfully'}, 200

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