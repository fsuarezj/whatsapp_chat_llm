from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from loguru import logger
from pprint import pformat
from contextvars import ContextVar
from typing import List, Optional

from pydantic import BaseModel, Field

from config.assistant_conf import GPT_MODEL
from ..base_state import BaseState
from .shop_assistant_prompt import build_system_prompt
from .cost_calculator_mixin import CostCalculatorMixin
from shop_api_client import shop_api_client

customer_phone_context: ContextVar[Optional[str]] = ContextVar("customer_phone", default=None)
current_order_context: ContextVar[Optional[int]] = ContextVar("current_order_id", default=None)


class OrderItemInput(BaseModel):
    product_name: str = Field(description="Exact product name from the catalog")
    quantity: int = Field(ge=1, description="Quantity ordered")


def _resolve_product(product_name: str) -> dict:
    product = shop_api_client.get_product_by_name(product_name)
    if not product:
        available = ", ".join(product["name"] for product in shop_api_client.list_products())
        raise ValueError(f"Unknown product '{product_name}'. Available products: {available}")
    return product


def _build_order_items(items: List[OrderItemInput]) -> tuple[list[dict], float]:
    order_items = []
    total = 0.0
    for item in items:
        product = _resolve_product(item.product_name)
        order_items.append({"product_id": product["id"], "quantity": item.quantity})
        total += product["price"] * item.quantity
    return order_items, total


@tool
def list_available_products() -> str:
    """List all products currently available in the shop."""
    products = shop_api_client.list_products()
    if not products:
        return "No products are currently available."
    lines = [f"- {product['name']}: {product['price']}" for product in products]
    return "Available products:\n" + "\n".join(lines)


@tool
def get_total_price(order: List[OrderItemInput]) -> float:
    """Calculate the total price for an order using live product prices."""
    _, total = _build_order_items(order)
    return total


@tool
def process_order(order: List[OrderItemInput], order_type: str = "pickup") -> str:
    """
    Create an order in the shop system for the current WhatsApp customer.

    Args:
        order: List of items with product_name and quantity.
        order_type: Either 'pickup' or 'delivery'.
    """
    phone = customer_phone_context.get()
    if not phone:
        raise ValueError("Customer phone number is unavailable for this conversation.")

    if order_type not in {"pickup", "delivery"}:
        raise ValueError("order_type must be 'pickup' or 'delivery'")

    order_items, total = _build_order_items(order)
    customer = shop_api_client.get_or_create_customer(phone_number=phone)
    created_order = shop_api_client.create_order(
        customer_id=customer["id"],
        items=order_items,
        order_type=order_type,
    )
    current_order_context.set(created_order["id"])
    logger.info(f"Created order {created_order['id']} for customer {customer['id']}")
    return (
        f"Order #{created_order['id']} created successfully. "
        f"Total amount: {created_order.get('total_amount', total)}. "
        f"Payment status: {created_order.get('payment_status', 'notPaid')}."
    )


@tool
def get_payment_status(order_id: int) -> str:
    """Get payment status for an order by order ID."""
    order = shop_api_client.get_order(order_id)
    return order.get("payment_status", "notPaid")


@tool
def request_order_payment(order_id: int, phone_number: Optional[str] = None) -> str:
    """Request MTN MoMo payment for an existing order."""
    order = shop_api_client.get_order(order_id)
    payer_phone = phone_number or customer_phone_context.get()
    if not payer_phone:
        raise ValueError("Phone number is required to request payment.")

    payment = shop_api_client.request_payment(
        order_id=order_id,
        phone_number=payer_phone,
        amount=float(order.get("total_amount", 0)),
        message=f"Payment for Xastrinxop order #{order_id}",
    )
    return (
        f"Payment request sent for order #{order_id}. "
        f"Status: {payment.get('status', 'PENDING')}. "
        f"Transaction ID: {payment.get('transaction_id', 'pending')}."
    )


class ShopAssistant(CostCalculatorMixin):
    def __init__(self):
        super().__init__()
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", build_system_prompt()),
            MessagesPlaceholder("messages"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        self._llm = ChatOpenAI(model=GPT_MODEL)
        self._tools = [
            list_available_products,
            get_total_price,
            process_order,
            get_payment_status,
            request_order_payment,
        ]

        agent = create_openai_functions_agent(self._llm, self._tools, self._prompt)
        self._runnable = AgentExecutor(agent=agent, tools=self._tools, verbose=False)

    def __call__(self, state: BaseState, config):
        customer_phone = state.get("customer_phone")
        if customer_phone:
            customer_phone_context.set(customer_phone)

        result = self._costs_invoke_OpenAI({"messages": state["messages"]})
        logger.debug("State: " + pformat(state))
        state["messages"] = state["messages"] + [{"role": "assistant", "content": result["output"]}]
        return {"messages": state["messages"][-1]}
