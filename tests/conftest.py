"""Utilidades compartidas por las pruebas."""
import json
from pathlib import Path

import pytest

from agents.analyst_agent import analysis_node
from agents.research_agent import research_node
from agents.supervisor_agent import decidir_siguiente, supervisor_node
from main import SOLICITUD_EJEMPLO
from state import crear_estado_inicial

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "fixtures"
ORIGEN = str(FIXTURES / "source")
DESTINO = str(FIXTURES / "targets")

CAMPOS_ACUMULATIVOS = ("research_findings", "analysis_findings", "agent_contributions", "errors",
                       "refinement_log", "routing_log", "uncertainties", "conflicts", "messages")


def aplicar(estado: dict, update: dict) -> dict:
    """Emula los reducers del estado: acumula listas, suma pasos y reemplaza el resto."""
    nuevo = dict(estado)
    for k, v in update.items():
        if k in CAMPOS_ACUMULATIVOS:
            nuevo[k] = list(estado.get(k, [])) + list(v)
        elif k == "step_count":
            nuevo[k] = estado.get(k, 0) + v
        else:
            nuevo[k] = v
    return nuevo


def avanzar_hasta(estado: dict, ruta_objetivo: str) -> dict:
    """Ejecuta supervisor y especialistas reales hasta que el supervisor elija ``ruta_objetivo``."""
    nodos = {"research": research_node, "analysis": analysis_node}
    for _ in range(10):
        if decidir_siguiente(estado)["ruta"] == ruta_objetivo:
            return estado
        estado = aplicar(estado, supervisor_node(estado))
        estado = aplicar(estado, nodos[estado["next_agent"]](estado))
    raise AssertionError(f"El supervisor nunca eligió {ruta_objetivo}")


@pytest.fixture
def estado_base():
    return crear_estado_inicial(SOLICITUD_EJEMPLO, [ORIGEN], [DESTINO])


@pytest.fixture
def estado_investigado(estado_base):
    return avanzar_hasta(estado_base, "analysis")


@pytest.fixture
def estado_analizado(estado_investigado):
    est = aplicar(estado_investigado, supervisor_node(estado_investigado))
    return aplicar(est, analysis_node(est))


@pytest.fixture
def escribir_json(tmp_path):
    def _escribir(nombre: str, contenido, crudo: bool = False) -> str:
        ruta = tmp_path / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido if crudo else json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(ruta)
    return _escribir


def firmas(hallazgos, archivo=None):
    """Conjunto de (severidad, categoría, ruta_json) para comparar con los resultados esperados."""
    return {(h["severidad"], h["categoria"], h["ruta_json"]) for h in hallazgos
            if archivo is None or Path(h["archivo"]).name == archivo}


def esperado(nombre: str) -> dict:
    return json.loads((FIXTURES / "expected_results" / nombre).read_text(encoding="utf-8"))


def firmas_esperadas(nombre: str):
    return {(h["severidad"], h["categoria"], h["ruta_json"]) for h in esperado(nombre)["hallazgos"]}
