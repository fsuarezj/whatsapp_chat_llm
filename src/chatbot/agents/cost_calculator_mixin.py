from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.runnables import Runnable
#from langfuse import Langfuse
#from langfuse.callback import CallbackHandler

from pprint import pformat
from loguru import logger

class Costs:
    total_costs = {}

    @staticmethod
    def get_total_costs():
        return Costs.total_costs
    
    @staticmethod
    def set_total_costs(new_costs):
        Costs.total_costs = new_costs

class CostCalculatorMixin:
    def __init__(self):
        self._runnable: Runnable
        super().__init__()
        #langfuse = Langfuse()
        #self._trace = langfuse.trace(name=self.__class__.__name__)
    
    def _costs_invoke_OpenAI(self, state: dict):
        #langfuse_handler = self._trace.get_langchain_handler()
        #langfuse_handler = CallbackHandler(self._trace)
        costs_dict = Costs.get_total_costs()
        logger.debug("Costs before calling:\n" + pformat(costs_dict))
        with get_openai_callback() as cb:
            result = self._runnable.invoke(state) #, config={"callbacks": [cb, langfuse_handler]})
            my_type = type(self).__name__
            if my_type in costs_dict:
                costs_dict[my_type] += cb.total_cost
            else:
                costs_dict[my_type] = cb.total_cost
        logger.info("Updated costs are:\n" + pformat(costs_dict))
        Costs.set_total_costs(costs_dict)
        return result
