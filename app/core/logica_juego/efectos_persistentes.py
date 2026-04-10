import random

from app.core.map_state import map_calculator
from app.schemas.estado_juego import EfectoActivo
from app.core.logica_juego.config_ataques_especiales import CONFIG_ATAQUES, TipoAtaque, TipoEfecto

from app.core.notifier import notifier

async def procesar_efectos_fin_de_turno(estado):
    nuevos_contagios = []
    num_jugadores = len(estado.jugadores)

    for territorio_id, data in estado.mapa.items():

        tropas_antes = data.get("units", 0)

        nuevos_contagios += procesar_territorio(territorio_id, data, num_jugadores)

        if data.get("units", 0) != tropas_antes or data.get("efectos"):
            await notifier.enviar_actualizacion_territorio(
                partida_id=estado.partida_id,
                territorio_id=territorio_id,
                data_territorio=data
            )

    if nuevos_contagios:
        aplicar_contagios(estado.mapa, nuevos_contagios)
        
        for t_id in nuevos_contagios:
            await notifier.enviar_actualizacion_territorio(
                partida_id=estado.partida_id, 
                territorio_id=t_id, 
                data_territorio=estado.mapa[t_id]
            )

    for jugador_data in estado.jugadores.values():
        jugador_data["efectos"] = procesar_efectos_genericos(
            jugador_data.get("efectos", [])
        )


def procesar_territorio(territorio_id, data, num_jugadores):
    efectos_vivos = []
    nuevos_contagios = []

    for efecto_dict in data.get("efectos", []):
        efecto = EfectoActivo(**efecto_dict)

        nuevos_contagios += aplicar_efecto_territorio(
            territorio_id, data, efecto, num_jugadores
        )

        if reducir_y_mantener(efecto):
            efectos_vivos.append(efecto.model_dump())

    data["efectos"] = efectos_vivos
    return nuevos_contagios


def aplicar_efecto_territorio(territorio_id, data, efecto, num_jugadores):
    if efecto.tipo_efecto == TipoEfecto.GRIPE_AVIAR:
        aplicar_gripe_aviar(data)

    elif efecto.tipo_efecto == TipoEfecto.CORONAVIRUS:
        return expandir_coronavirus(territorio_id, efecto, num_jugadores)

    return []


def aplicar_gripe_aviar(data):
    dano = CONFIG_ATAQUES[TipoAtaque.GRIPE_AVIAR]["dano_por_turno"]
    data["units"] = max(0, data["units"] - dano)

    if data["units"] == 0:
        data["owner_id"] = "neutral"


def expandir_coronavirus(territorio_id, efecto, num_jugadores):
    prob = CONFIG_ATAQUES[TipoAtaque.CORONAVIRUS]["probabilidad_expansion"]

    # Duracion depende del numero de jugadores
    dur = CONFIG_ATAQUES[TipoAtaque.CORONAVIRUS]["rondas_duracion"] * num_jugadores

    vecinos = map_calculator.obtener_vecinos(territorio_id)
    contagios = []

    for vecino in vecinos:
        if random.random() <= prob:
            contagios.append({
                "destino": vecino,
                "efecto": EfectoActivo(
                    tipo_efecto=TipoEfecto.CORONAVIRUS,
                    duracion_restante=dur,
                    origen_jugador_id=efecto.origen_jugador_id
                )
            })

    return contagios


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
    efecto.duracion_restante -= 1
    return efecto.duracion_restante > 0