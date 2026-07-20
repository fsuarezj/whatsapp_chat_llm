import unittest
from unittest.mock import patch

from chatbot.agents.shop_assistant import OrderItemInput, _build_order_items, customer_phone_context, process_order


class ShopAssistantTests(unittest.TestCase):
    def setUp(self):
        self.products = [
            {"id": 1, "name": "Greek yoghurt", "price": 6.0, "is_active": True},
            {"id": 2, "name": "Labneh", "price": 7.0, "is_active": True},
        ]
        self.client_patch = patch("chatbot.agents.shop_assistant.shop_api_client")
        self.mock_client = self.client_patch.start()
        self.mock_client.list_products.return_value = self.products

        def get_by_name(name: str):
            for product in self.products:
                if product["name"].lower() == name.strip().lower():
                    return product
            return None

        self.mock_client.get_product_by_name.side_effect = get_by_name

    def tearDown(self):
        self.client_patch.stop()

    def test_build_order_items(self):
        items = [
            OrderItemInput(product_name="Greek yoghurt", quantity=2),
            OrderItemInput(product_name="Labneh", quantity=1),
        ]
        order_items, total = _build_order_items(items)
        self.assertEqual(
            order_items,
            [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
        )
        self.assertEqual(total, 19.0)

    def test_process_order_uses_customer_phone(self):
        self.mock_client.get_or_create_customer.return_value = {
            "id": 10,
            "phone_number": "34600111222",
        }
        self.mock_client.create_order.return_value = {
            "id": 99,
            "total_amount": 12.0,
            "payment_status": "notPaid",
        }

        token = customer_phone_context.set("34600111222")
        try:
            result = process_order.invoke(
                {
                    "order": [OrderItemInput(product_name="Greek yoghurt", quantity=2)],
                    "order_type": "pickup",
                }
            )
        finally:
            customer_phone_context.reset(token)

        self.assertIn("Order #99", result)
        self.mock_client.create_order.assert_called_once()


if __name__ == "__main__":
    unittest.main()
