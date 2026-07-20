import os
from typing import Any, Dict, List, Optional

import requests
from loguru import logger


class ShopApiClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("SHOP_API_URL", "http://localhost:5000")).rstrip("/")
        self.username = username or os.getenv("SHOP_API_USERNAME", "bot")
        self.password = password or os.getenv("SHOP_API_PASSWORD", "BotService123")
        self._access_token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        if not self._access_token:
            self.login()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def login(self) -> None:
        response = requests.post(
            f"{self.base_url}/api/login",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]

    def list_products(self, active_only: bool = True) -> List[Dict[str, Any]]:
        response = requests.get(f"{self.base_url}/api/products", headers=self._headers(), timeout=30)
        response.raise_for_status()
        products = response.json()
        if active_only:
            products = [product for product in products if product.get("is_active", True)]
        return products

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        normalized = name.strip().lower()
        for product in self.list_products():
            if product["name"].strip().lower() == normalized:
                return product
        return None

    def get_or_create_customer(self, phone_number: str, name: Optional[str] = None) -> Dict[str, Any]:
        customers = requests.get(f"{self.base_url}/api/customers", headers=self._headers(), timeout=30)
        customers.raise_for_status()
        for customer in customers.json():
            if customer["phone_number"] == phone_number:
                return customer

        response = requests.post(
            f"{self.base_url}/api/customers",
            json={"phone_number": phone_number, "name": name or phone_number},
            headers=self._headers(),
            timeout=30,
        )
        if response.status_code == 409:
            customers = requests.get(f"{self.base_url}/api/customers", headers=self._headers(), timeout=30)
            customers.raise_for_status()
            for customer in customers.json():
                if customer["phone_number"] == phone_number:
                    return customer
        response.raise_for_status()
        return response.json()

    def create_order(
        self,
        customer_id: int,
        items: List[Dict[str, int]],
        order_type: str = "pickup",
    ) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/orders",
            json={
                "customer_id": customer_id,
                "order_type": order_type,
                "items": items,
                "payment_status": "notPaid",
                "delivery_status": "notDelivered",
            },
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_order(self, order_id: int) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/api/orders/{order_id}",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def request_payment(self, order_id: int, phone_number: str, amount: float, message: Optional[str] = None) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/payments/request",
            json={
                "order_id": order_id,
                "phone_number": phone_number,
                "amount": amount,
                "message": message or f"Payment for order {order_id}",
            },
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


shop_api_client = ShopApiClient()
