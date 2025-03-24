from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig, RunnablePassthrough
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langgraph.prebuilt import ToolNode
from loguru import logger
from pprint import pformat
from langchain_core.messages import HumanMessage, AIMessage
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, model_validator, ValidatorFunctionWrapHandler, ValidationError
from typing import Self

from config.assistant_conf import GPT_MODEL
from ..base_state import BaseState
from .shop_assistant_prompt import prompt_shop_assistant
from .cost_calculator_mixin import CostCalculatorMixin

class Product(str, Enum):
    drinking = "Drinking yoghurt"
    regular = "Regular yoghurt"
    greek = "Greek yoghurt"
    strawberry = "Strawberry yoghurt"
    mango = "Mango yoghurt"
    vanilla = "Vanilla yoghurt"
    labneh = "Labneh"
    labneh_deluxe = "Labneh deluxe"
    cottage = "Cottage cheese"
    sour_milk = "Sour milk"

class OrderItem(BaseModel):
    product: Product
    quantity: int

#    @model_validator(mode="wrap")
#    @classmethod
#    def model_wrap_validate(cls, data: dict, handler: ValidatorFunctionWrapHandler) -> Self:
#        try:
#            print("EOOOOO")
#            print(data)
#            result = handler(data)
#        except ValidationError as e:
#            raise ValueError(f"Invalid order: {e}") from e
#        return result

@tool
def process_order(order: List[OrderItem]) -> None:
    """
    Process an order by iterating through items and their quantities.

    This function takes a list of OrderItem objects and processes each item in the order.
    Each OrderItem contains a Product enum value and its quantity.

    Args:
        order (List[OrderItem]): A list of OrderItem objects, where each OrderItem contains:
            - product (Product): The product enum value (e.g., "Labneh", "Greek yoghurt")
            - quantity (int): The quantity ordered
            Example: [
                OrderItem(product=Product.labneh, quantity=2),
                OrderItem(product=Product.greek, quantity=1)
            ]

    Returns:
        None

    Logs:
        - Warning level log of full order
        - Warning level log for each item being processed
    """
    logger.warning(f"Processing order: {order}")
    for item in order:
        logger.warning(f"Processing {item.quantity} units of {item.product}")

def get_price(item: str, quantity: int) -> int:
    """
    Get the price of an item.

    Args:
        item (str): The name of the item.
        quantity (int): The quantity of the item.

    Returns:
        float: The price of the item.
    """
    return 1000 * quantity

@tool
def get_total_price(order: List[OrderItem]) -> int:
    """
    Get the total price of an order.

    Args:
        order (dict): A dictionary containing items as keys and quantities as values.
                     Example: {"item1": 2, "item2": 1}

    Returns:
        float: The total price of the order.
    """
    return sum(get_price(item.product, item.quantity) for item in order)

@tool
def get_payment_status(id: int) -> str:
    """
    Get the status of an order.

    Args:
        id (int): The id of the payment.

    Returns:
        str: The status of the payment.
    """
    if id % 2 == 0:
        return "paid"
    else:
        return "not paid"

class ShopAssistant(CostCalculatorMixin):


    def __init__(self):
        super().__init__()
        prompt = [(i["role"], i["content"]) for i in prompt_shop_assistant["prompt"]]
        system_prompt = list(filter(lambda x: x[0] == "system", prompt))
        self._prompt = ChatPromptTemplate.from_messages([
            *system_prompt,
            MessagesPlaceholder("messages"),
            MessagesPlaceholder("agent_scratchpad")
        ])

        process_order_tool = process_order
        get_total_price_tool = get_total_price
        get_payment_status_tool = get_payment_status

        self._llm = ChatOpenAI(model=GPT_MODEL)
        tools = [
            process_order,
            get_total_price,
            get_payment_status
        ]

        # Create agent
        agent = create_openai_functions_agent(self._llm, tools, self._prompt)
        
        # Create executor
        self._runnable = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True  # Set to True to see the agent's thought process
        )
    #    #self._runnable = self._include_langfuse_support(self._runnable)

    #def __call__(self, state: BaseState, config: RunnableConfig):
    #    logger.debug("CALLING ShopAssistant")
    #    result = self._costs_invoke_OpenAI({
    #        "messages": state["messages"]
    #    })
    #    state["messages"] = state["messages"] + [result]
    #    return {"messages": result}
    
    def __call__(self, state: BaseState, config: RunnableConfig):
        #TODO: logger.log("AGENT_CALL", "CALLING ShopAssistant")
        result = self._costs_invoke_OpenAI({
            "messages": state["messages"]
        })
        logger.debug("State: " + pformat(state))
        state["messages"] = state["messages"] + [{"role": "assistant", "content": result["output"]}]
        return {"messages": state["messages"][-1]}
