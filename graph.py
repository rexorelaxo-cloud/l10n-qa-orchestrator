"""Grafo principal del L10n QA Orchestrator (LangGraph ``StateGraph``).

Topología jerárquica con Supervisor:

    START → supervisor ─┬→ research ──┐
                        ├→ analysis ──┼→ supervisor (o validation si queda un solo paso)
                        ├→ validation ─┬→ supervisor (si necesita refinamiento)
                        └→ END         └→ END (resultado validado o fallo controlado)

Las rutas surgen de las decisiones del Supervisor (aristas condicionales), no de una secuencia fija.
"""
from typing import Callable, Literal, Optional

from langgraph.graph import END, START, StateGraph

from agents.analyst_agent import analysis_node
from agents.research_agent import research_node
from agents.supervisor_agent import enrutar_supervisor, supervisor_node
from agents.validation_agent import enrutar_validacion, validation_node
from state import L10nState


def enrutar_tras_especialista(state: L10nState) -> Literal["supervisor", "validation"]:
    """Los especialistas devuelven el control al Supervisor.

    Excepción de seguridad: si solo queda una ejecución disponible, se pasa directamente a la
    validación para cerrar de forma controlada sin superar ``max_steps``.
    """
    if state["step_count"] >= state["max_steps"] - 1:
        return "validation"
    return "supervisor"


def construir_grafo(
    research: Optional[Callable] = None,
    analysis: Optional[Callable] = None,
    supervisor: Optional[Callable] = None,
    validation: Optional[Callable] = None,
):
    """Construye y compila el grafo. Los parámetros permiten sustituir nodos (útil en pruebas)."""
    g = StateGraph(L10nState)
    g.add_node("supervisor", supervisor or supervisor_node)
    g.add_node("research", research or research_node)
    g.add_node("analysis", analysis or analysis_node)
    g.add_node("validation", validation or validation_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor", enrutar_supervisor,
        {"research": "research", "analysis": "analysis", "validation": "validation", "END": END},
    )
    g.add_conditional_edges("research", enrutar_tras_especialista,
                            {"supervisor": "supervisor", "validation": "validation"})
    g.add_conditional_edges("analysis", enrutar_tras_especialista,
                            {"supervisor": "supervisor", "validation": "validation"})
    g.add_conditional_edges("validation", enrutar_validacion, {"supervisor": "supervisor", "END": END})
    return g.compile()


graph = construir_grafo()


def obtener_mermaid(grafo=None) -> str:
    """Diagrama Mermaid del grafo compilado (no requiere dependencias opcionales)."""
    return (grafo or graph).get_graph().draw_mermaid()


def guardar_diagrama_png(ruta: str, grafo=None) -> bool:
    """Intenta generar un PNG del grafo con LangGraph (requiere red o dependencias opcionales).

    Devuelve ``True`` si se generó. Si falla, el diagrama Mermaid sigue disponible.
    """
    try:
        png = (grafo or graph).get_graph().draw_mermaid_png()
        with open(ruta, "wb") as f:
            f.write(png)
        return True
    except Exception:
        return False
