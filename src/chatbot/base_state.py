from typing import Annotated, List
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from loguru import logger

def add_cost(state: dict, costs: dict) -> object:
    if state:
        new_costs = {i: state.get(i,0) + costs.get(i,0) for i in set(state).union(costs)}
    else:
        new_costs = costs
    return BaseState(new_costs)

class BaseState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    #costs: Annotated[dict,add_cost]
    next: str
