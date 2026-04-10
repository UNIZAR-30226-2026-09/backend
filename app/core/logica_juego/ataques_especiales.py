import random
from typing import Callable, Dict, Any
import math
from app.core.map_state import map_calculator
from app.schemas.estado_juego import EfectoActivo

from app.core.logica_juego.config_ataques_especiales import CONFIG_ATAQUES, TipoAtaque, TipoEfecto

REGISTRO_ATAQUES: Dict[str, Callable] = {}

def registrar_ataque(nombre: str):
    def decorador(func: Callable):
        REGISTRO_ATAQUES[nombre] = func
        return func
    return decorador

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def validar_rango(origen: str, destino: str, rango_maximo: int, rango_exacto: bool = False):
    distancia = map_calculator.calcular_distancia(origen, destino)
    if distancia == -1:
        raise ValueError("No hay ruta posible hacia el objetivo.")
    if rango_exacto and distancia != rango_maximo:
        raise ValueError(f"El objetivo debe estar a exactamente {rango_maximo} saltos.")
    if not rango_exacto and distancia > rango_maximo:
        raise ValueError(f"Objetivo fuera de rango. Máximo: {rango_maximo}, Actual: {distancia}")

def aplicar_dano_porcentual(territorio: dict, porcentaje: float):
    bajas = math.ceil(territorio["units"] * porcentaje)
    territorio["units"] = max(0, territorio["units"] - bajas)

     # Si ya no quedan tropas en el territorio, queda vacio
    if territorio["units"] == 0:
        territorio["owner_id"] = "neutral"

# ----------------------------------------------------------------------------
# Ataques
# ----------------------------------------------------------------------------
@registrar_ataque(TipoAtaque.MORTERO_TACTICO)
def ejecutar_mortero_tactico(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.MORTERO_TACTICO]
    validar_rango(origen, destino, rango_maximo=cfg["rango"], rango_exacto=True)
    
    bajas = random.randint(cfg["dano_min"], cfg["dano_max"])
    estado.mapa[destino]["units"] = max(0, estado.mapa[destino]["units"] - bajas)

@registrar_ataque(TipoAtaque.MISIL_CRUCERO)
def ejecutar_misil_crucero(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.MISIL_CRUCERO]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    aplicar_dano_porcentual(estado.mapa[destino], cfg["dano_porcentaje"])

@registrar_ataque(TipoAtaque.CABEZA_NUCLEAR)
def ejecutar_cabeza_nuclear(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.CABEZA_NUCLEAR]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    aplicar_dano_porcentual(estado.mapa[destino], cfg["dano_porcentaje"])
    
@registrar_ataque(TipoAtaque.BOMBA_RACIMO)
def ejecutar_bomba_racimo(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.BOMBA_RACIMO]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    aplicar_dano_porcentual(estado.mapa[destino], cfg["dano_objetivo"])
    
    vecinos = map_calculator.obtener_vecinos(destino)
    for vecino in vecinos:
        aplicar_dano_porcentual(estado.mapa[vecino], cfg["dano_colindantes"])

@registrar_ataque(TipoAtaque.GRIPE_AVIAR)
def ejecutar_gripe_aviar(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.GRIPE_AVIAR]
    nuevo_efecto = EfectoActivo(
        tipo_efecto=TipoEfecto.GRIPE_AVIAR, 
        duracion_restante=cfg["duracion"], 
        origen_jugador_id=atacante_id
    )
    estado.mapa[destino]["efectos"].append(nuevo_efecto.model_dump())

@registrar_ataque(TipoAtaque.VACUNA_UNIVERSAL)
def ejecutar_vacuna(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.VACUNA_UNIVERSAL]
    if estado.mapa[destino]["owner_id"] != atacante_id:
        raise ValueError("Solo puedes vacunar tus propios territorios.")
    
    estado.mapa[destino]["efectos"] = [
        e for e in estado.mapa[destino]["efectos"] 
        if e["tipo_efecto"] not in cfg["enfermedades_curables"]
    ]

@registrar_ataque(TipoAtaque.CORONAVIRUS)
def ejecutar_coronavirus(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.CORONAVIRUS]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    aplicar_dano_porcentual(estado.mapa[destino], cfg["dano_inicial"])
    
    num_jugadores = len(estado.jugadores)
    duracion_turnos = cfg["rondas_duracion"] * num_jugadores

    nuevo_efecto = EfectoActivo(
        tipo_efecto=TipoEfecto.CORONAVIRUS, 
        duracion_restante=duracion_turnos, 
        origen_jugador_id=atacante_id
    )
    estado.mapa[destino]["efectos"].append(nuevo_efecto.model_dump())

@registrar_ataque(TipoAtaque.FATIGA)
def ejecutar_fatiga(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.FATIGA]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    nuevo_efecto = EfectoActivo(
        tipo_efecto=TipoEfecto.FATIGA, 
        duracion_restante=cfg["duracion"], 
        origen_jugador_id=atacante_id
    )
    estado.mapa[destino]["efectos"].append(nuevo_efecto.model_dump())


@registrar_ataque(TipoAtaque.INHIBIDOR_SENAL)
def ejecutar_inhibidor(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.INHIBIDOR_SENAL]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    nuevo_efecto = EfectoActivo(tipo_efecto=TipoEfecto.INHIBIDOR_SENAL, duracion_restante=cfg["duracion"], origen_jugador_id=atacante_id)
    estado.mapa[destino]["efectos"].append(nuevo_efecto.model_dump())

@registrar_ataque(TipoAtaque.PROPAGANDA_SUBVERSIVA)
def ejecutar_propaganda(estado, atacante_id: str, origen: str, destino: str):
    cfg = CONFIG_ATAQUES[TipoAtaque.PROPAGANDA_SUBVERSIVA]
    validar_rango(origen, destino, rango_maximo=cfg["rango"])
    
    nuevo_efecto = EfectoActivo(tipo_efecto=TipoEfecto.PROPAGANDA, duracion_restante=cfg["duracion"], origen_jugador_id=atacante_id)
    estado.mapa[destino]["efectos"].append(nuevo_efecto.model_dump())

@registrar_ataque(TipoAtaque.MURO_FRONTERIZO)
def ejecutar_muro(estado, atacante_id: str, origen: str, destino: str):
    validar_rango(origen, destino, rango_maximo=1, rango_exacto=True)
    
    # El muro bloquea ambas direcciones de la frontera
    efecto_origen = EfectoActivo(tipo_efecto=TipoEfecto.MURO, duracion_restante=1, origen_jugador_id=atacante_id).model_dump()
    efecto_origen["bloquea_hacia"] = destino
    estado.mapa[origen]["efectos"].append(efecto_origen)

    efecto_destino = EfectoActivo(tipo_efecto=TipoEfecto.MURO, duracion_restante=1, origen_jugador_id=atacante_id).model_dump()
    efecto_destino["bloquea_hacia"] = origen
    estado.mapa[destino]["efectos"].append(efecto_destino)

@registrar_ataque(TipoAtaque.SANCIONES_INTERNACIONALES)
def ejecutar_sanciones(estado, atacante_id: str, origen: str, destino: str):
    # Destino es el id del jugador enemigo
    jugador_objetivo = estado.jugadores.get(destino)
    if not jugador_objetivo:
        raise ValueError("Jugador objetivo no encontrado.")
    
    if "efectos" not in jugador_objetivo:
        jugador_objetivo["efectos"] = []
        
    jugador_objetivo["efectos"].append({
        "tipo_efecto": TipoEfecto.SANCIONES, 
        "duracion_restante": 1, 
        "origen_jugador_id": atacante_id
    })

# ----------------------------------------------------------------------------
# Funcion principal
# ----------------------------------------------------------------------------
def procesar_lanzamiento_guerra_tecnologica(estado, atacante_id: str, tipo_ataque: str, origen: str, destino: str):
    jugador = estado.jugadores.get(atacante_id)
    
    if tipo_ataque not in jugador["tecnologias_compradas"]:
        raise ValueError(f"El jugador no ha investigado/comprado {tipo_ataque}.")
    
    if tipo_ataque not in REGISTRO_ATAQUES:
        raise ValueError(f"Ataque {tipo_ataque} no está implementado.")
    
    t_origen = estado.mapa.get(origen)
    if t_origen:
        efectos = t_origen.get("efectos", []) if isinstance(t_origen, dict) else getattr(t_origen, "efectos", [])
        for e in efectos:
            tipo = e.get("tipo_efecto") if isinstance(e, dict) else getattr(e, "tipo_efecto", None)
            if tipo == TipoEfecto.INHIBIDOR_SENAL:
                raise ValueError("Tus comunicaciones están inhibidas. No puedes coordinar lanzamientos especiales desde este territorio.")

    REGISTRO_ATAQUES[tipo_ataque](estado, atacante_id, origen, destino)