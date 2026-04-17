import random
import math

from app.schemas.combate import ResultadoAtaqueCompleto
from app.core.logica_juego.config_ataques_especiales import TipoEfecto

from app.core.notifier import notifier

def validar_tropas(tropas_atacantes: int, tropas_defensoras: int):
    if tropas_atacantes < 1 or tropas_defensoras < 1:
        raise ValueError("Debe haber al menos 1 tropa atacante y 1 defensora.")
    if tropas_atacantes > 3:
        raise ValueError("El atacante no puede usar más de 3 tropas.")

def calcular_dados(tropas_atacantes: int, tropas_defensoras: int):
    num_dados_atacante = tropas_atacantes - 1
    num_dados_defensor = tropas_defensoras

    return num_dados_atacante, num_dados_defensor


def tirar_dados(num_dados: int):
    dados = [random.randint(1, 6) for _ in range(num_dados)]
    return sorted(dados, reverse=True)


def comparar_dados(dados_atacante, dados_defensor):
    bajas_atacante = 0
    bajas_defensor = 0

    for a, d in zip(dados_atacante, dados_defensor):
        if a > d:
            bajas_defensor += 1
        else:
            bajas_atacante += 1

    return bajas_atacante, bajas_defensor


def calcular_estado_final(tropas_defensoras, bajas_defensor):
    tropas_restantes = tropas_defensoras - bajas_defensor
    victoria = tropas_restantes <= 0
    return tropas_restantes, victoria




async def resolver_colocacion_tropas(jugador_estado, t_destino, tropas_a_poner: int, data_territorio: dict, jugadores_estado: dict, partida_id):
    
    jugador_estado.tropas_reserva -= tropas_a_poner
    t_destino.units += tropas_a_poner

    # notifier.enviar_tropas_colocadas


def resolver_fortificacion(estado_mapa: dict, origen_id: str, destino_id: str, tropas: int):
    estado_mapa[origen_id]["units"] -= tropas
    estado_mapa[destino_id]["units"] += tropas

def resolver_ataque_completo(tropas_origen: int, tropas_destino: int) -> ResultadoAtaqueCompleto:
    """Bucle completo hasta conquista o hasta quedarse con 1 tropa en origen."""
    total_bajas_atacante = 0
    total_bajas_defensor = 0

    while tropas_origen > 1 and tropas_destino > 0:

        dados_ataq_count, dados_def_count = calcular_dados(tropas_origen, tropas_destino)

        dados_ataq = tirar_dados(dados_ataq_count)
        dados_def = tirar_dados(dados_def_count)

        bajas_a, bajas_d = comparar_dados(dados_ataq, dados_def)

        tropas_origen -= bajas_a
        tropas_destino -= bajas_d
        total_bajas_atacante += bajas_a
        total_bajas_defensor += bajas_d

    return ResultadoAtaqueCompleto(
        victoria_atacante=tropas_destino <= 0,
        bajas_atacante=total_bajas_atacante,
        bajas_defensor=total_bajas_defensor,
        tropas_restantes_origen=tropas_origen,
        tropas_restantes_defensor=tropas_destino,
    )

def aplicar_resultado_combate(t_origen, t_destino, resultado: ResultadoAtaqueCompleto):
    t_origen.units = resultado.tropas_restantes_origen
    t_destino.units = resultado.tropas_restantes_defensor

def ejecutar_conquista(t_destino, jugador_estado, atacante_id: str, origen_id: str, destino_id: str):
    t_destino.owner_id = atacante_id
    jugador_estado.movimiento_conquista_pendiente = True
    jugador_estado.origen_conquista = origen_id
    jugador_estado.destino_conquista = destino_id