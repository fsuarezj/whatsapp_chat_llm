from langgraph.graph.state import CompiledStateGraph
from loguru import logger

class DiagramDrawerMixin:
    def __init__(self):
        self._graph : CompiledStateGraph
        self._unthemed_diagram : str = None

    def generate_stream_response(self, input, state):
        pass

#    def get_diagram(self, active = "__start__") -> str:
#        diagram = """
#            %%{init: {'theme':'base'}}%%
#            graph TD
#                __start__ --> __end__
#            classDef default fill:#EEE,stroke:#000,stroke-width:1px
#            classDef active fill:#EAA,stroke:#000,stroke-width:3px
#            """
#        diagram += f"class {active} active"
#        logger.debug("GRAPH: \n" + diagram)
#        return diagram

    def _set_diagram(self) -> str:
        diagram = self._graph.get_graph().draw_mermaid()
        diagram = diagram.splitlines()
        theme = "%%{init: {'theme':'base'}}%%"
        diagram[0] = theme
        diagram = diagram[:-3]
        diagram.append("\tclassDef default fill:#EEE,stroke:#000,stroke-width:1px")
        diagram.append("\tclassDef active fill:#EAA,stroke:#000,stroke-width:3px")
        result = "\n".join(diagram)
        logger.debug("\nGRAPH: \n" + result)
        return result

    def get_diagram(self, active = "__start__") -> str:
        if not self._unthemed_diagram:
            self._unthemed_diagram = self._set_diagram()
        diagram = self._unthemed_diagram.splitlines()
        diagram.append("\tclass " + active + " active")
        diagram = "\n".join(diagram)
        return diagram