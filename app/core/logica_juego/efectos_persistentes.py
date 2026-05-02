import random

from app.core.map_state import map_calculator
from app.schemas.estado_juego import EfectoActivo
from app.core.logica_juego.config_ataques_especiales import CONFIG_ATAQUES, TipoAtaque, TipoEfecto

from app.core.logica_juego.ataques_especiales import aplicar_dano_porcentual, aplicar_dano_fijo

from app.core.notifier import notifier

# ----------------------------------------------------------------------------
# Funciones principales
# ----------------------------------------------------------------------------


async def procesar_efectos_fin_de_turno(estado):
    """
    Limpia duraciones de efectos y expande virus.
    """
    nuevos_contagios = await procesar_todos_los_territorios(estado)

    if nuevos_contagios:
        await aplicar_y_notificar_contagios(estado, nuevos_contagios)

    actualizar_efectos_jugadores(estado)


async def procesar_efectos_inicio_turno(estado, jugador_id: str):
    """
    Aplica el daño de enfermedades y efectos negativos al inicio del turno del jugador.
    """
    for territorio_id, data in estado.mapa.items():
        if data.get("owner_id") != jugador_id:
            continue
            
        tropas_antes = data.get("units", 0)
        
        # Recorremos los efectos para aplicar el daño
        for efecto in data.get("efectos", []):
            if efecto["tipo_efecto"] == TipoEfecto.GRIPE_AVIAR:
                # Quita X tropas fijas
                aplicar_gripe_aviar(data) 
            elif efecto["tipo_efecto"] == TipoEfecto.CORONAVIRUS:
                # Quita Y% de tropas
                aplicar_dano_coronavirus(data) 

        if data.get("units", 0) <= 0:
            data["units"] = 0
            data["efectos"] = []
            data["owner_id"] = "neutral"

        if data.get("units", 0) != tropas_antes:

            await notifier.enviar_actualizacion_territorio(
                partida_id=estado.partida_id,
                territorio_id=territorio_id,
                data_territorio=data
            )



# ----------------------------------------------------------------------------
# Aplicar daños
# ----------------------------------------------------------------------------

def aplicar_dano_coronavirus(data):
    """Aplica el daño porcentual recurrente configurado para el coronavirus."""
    cfg = CONFIG_ATAQUES[TipoAtaque.CORONAVIRUS]
    porcentaje = cfg.get("dano_recurrente")
    aplicar_dano_porcentual(data, porcentaje)

def aplicar_gripe_aviar(data):
    dano = CONFIG_ATAQUES[TipoAtaque.GRIPE_AVIAR]["dano_por_turno"]
    aplicar_dano_fijo(data, dano)

# ----------------------------------------------------------------------------
# Tiempo y expansiones
# ----------------------------------------------------------------------------
async def procesar_todos_los_territorios(estado) -> list:
    """Recorre el mapa y devuelve la lista de nuevos contagios detectados."""
    nuevos_contagios = []
    num_jugadores = len(estado.jugadores)

    for territorio_id, data in estado.mapa.items():
        # Copia para solo enviar ws de aquellos que se han modificado
        efectos_antes = list(data.get("efectos", []))


        contagios_territorio = actualizar_estado_efectos_territorio(data, territorio_id, num_jugadores)
        nuevos_contagios += contagios_territorio
        
        if efectos_antes != data.get("efectos", []):
            await notifier.enviar_actualizacion_territorio(estado.partida_id, territorio_id, data)
        
    return nuevos_contagios

def actualizar_estado_efectos_territorio(data, territorio_id, num_jugadores) -> list:
    """Actualiza duraciones y calcula expansiones para UN territorio."""
    efectos_vivos = []
    contagios = []

    for efecto_dict in data.get("efectos", []):
        efecto = EfectoActivo(**efecto_dict)
        
        # si es coronaviros, expandimos
        if efecto.tipo_efecto == TipoEfecto.CORONAVIRUS:
            contagios += expandir_coronavirus(territorio_id, efecto, num_jugadores)
        
        # Reducidos y comprobamos fin
        if reducir_y_mantener(efecto):
            efectos_vivos.append(efecto.model_dump())

    data["efectos"] = efectos_vivos
    return contagios

def expandir_coronavirus(territorio_id, efecto, num_jugadores):
    prob = CONFIG_ATAQUES[TipoAtaque.CORONAVIRUS]["probabilidad_expansion"]

    vecinos = map_calculator.obtener_vecinos(territorio_id)
    contagios = []

    for vecino in vecinos:
        if random.random() <= prob:
            contagios.append({
                "destino": vecino,
                "efecto": EfectoActivo(
                    tipo_efecto=TipoEfecto.CORONAVIRUS,
                    # Duracion es la que le quede, no se recalcula
                    duracion=efecto.duracion,
                    origen_jugador_id=efecto.origen_jugador_id
                )
            })

    return contagios


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

async def aplicar_y_notificar_contagios(estado, contagios):
    """Aplica los contagios al mapa y envía las notificaciones necesarias."""
    aplicar_contagios(estado.mapa, contagios)
    for c in contagios:
        t_id = c["destino"]
        await notifier.enviar_actualizacion_territorio(estado.partida_id, t_id, estado.mapa[t_id])

def actualizar_efectos_jugadores(estado):
    """Limpia los efectos que expiran a nivel de jugador."""
    for jugador_id, jugador_data in estado.jugadores.items():
        jugador_data["efectos"] = procesar_efectos_genericos(jugador_data.get("efectos", []))

def aplicar_contagios(mapa, contagios):
    for c in contagios:
        destino = mapa[c["destino"]]
        efectos = destino.get("efectos", [])

        if not esta_infectado(efectos, TipoEfecto.CORONAVIRUS):
            efectos.append(c["efecto"].model_dump())
            destino["efectos"] = efectos


def esta_infectado(efectos, tipo):
    return any(e["tipo_efecto"] == tipo for e in efectos)


def procesar_efectos_genericos(efectos):
    efectos_vivos = []

    for efecto_dict in efectos:
        efecto = EfectoActivo(**efecto_dict)

        if reducir_y_mantener(efecto):
            efectos_vivos.append(efecto.model_dump())

    return efectos_vivos


def reducir_y_mantener(efecto):
    efecto.duracion -= 1
    return efecto.duracion > 0