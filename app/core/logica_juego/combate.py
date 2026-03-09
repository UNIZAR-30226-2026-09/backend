import random
from app.schemas.combate import ResultadoCombate


def validar_tropas(tropas_atacantes: int, tropas_defensoras: int):
    if tropas_atacantes < 1 or tropas_defensoras < 1:
        raise ValueError("Debe haber al menos 1 tropa atacante y 1 defensora.")
    if tropas_atacantes > 3:
        raise ValueError("El atacante no puede usar más de 3 tropas.")


def calcular_dados(tropas_atacantes: int, tropas_defensoras: int):
    num_dados_atacante = tropas_atacantes
    num_dados_defensor = min(tropas_defensoras, 2)
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


def resolver_tirada(tropas_atacantes_enviadas: int, tropas_defensoras_totales: int) -> ResultadoCombate:
    validar_tropas(tropas_atacantes_enviadas, tropas_defensoras_totales)

    num_a, num_d = calcular_dados(tropas_atacantes_enviadas, tropas_defensoras_totales)

    dados_atacante = tirar_dados(num_a)
    dados_defensor = tirar_dados(num_d)

    bajas_a, bajas_d = comparar_dados(dados_atacante, dados_defensor)

    tropas_restantes, victoria = calcular_estado_final(tropas_defensoras_totales, bajas_d)

    return ResultadoCombate(
        dados_atacante=dados_atacante,
        dados_defensor=dados_defensor,
        bajas_atacante=bajas_a,
        bajas_defensor=bajas_d,
        victoria_atacante=victoria,
        tropas_restantes_defensor=tropas_restantes
    )