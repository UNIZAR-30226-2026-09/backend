import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usuario import User
from app.crud import crud_estadisticas
from app.schemas.usuario import EstadisticaRead

# IMPORTANTE: Importamos el estado del mapa para leer IDs válidos
from app.core.map_state import game_map_state

@pytest.mark.asyncio
async def test_estadisticas_calculos_y_ranking(db: AsyncSession):

    # ---------------------------------------------------------
    # 0. SETUP DE MAPA: Cogemos 3 IDs reales para el test
    # ---------------------------------------------------------
    ids_reales = list(game_map_state.comarcas.keys())
    id_1 = ids_reales[0] # Sustituto de "Zaragoza"
    id_2 = ids_reales[1] # Sustituto de "Huesca"
    id_3 = ids_reales[2] # Sustituto de "Teruel"

    # Sacamos el nombre real de la comarca 1 para verificar el modelo
    nombre_esperado_id_1 = game_map_state.comarcas[id_1].name

    # ---------------------------------------------------------
    # 1. SETUP: Creamos tres usuarios para la prueba
    # ---------------------------------------------------------
    u1 = User(username="JugadorPro", email="pro@test.com", passwd_hash="123")
    u2 = User(username="JugadorMedio", email="medio@test.com", passwd_hash="123")
    u3 = User(username="JugadorNovato", email="novato@test.com", passwd_hash="123")

    db.add_all([u1, u2, u3])
    await db.commit()

    # ---------------------------------------------------------
    # 2. SIMULAR PARTIDAS
    # ---------------------------------------------------------

    for _ in range(3):
        await crud_estadisticas.registrar_fin_partida(
            db, "JugadorPro", es_ganador=True,
            comarcas_conquistadas={id_1: 1, id_2: 1},
            soldados_matados_en_partida=20
        )

    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorPro", es_ganador=False,
        comarcas_conquistadas={id_1: 2},
        soldados_matados_en_partida=40
    )

    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorMedio", es_ganador=True,
        comarcas_conquistadas={id_3: 3},
        soldados_matados_en_partida=150
    )
    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorMedio", es_ganador=False,
        comarcas_conquistadas={},
        soldados_matados_en_partida=0
    )

    for _ in range(10):
        await crud_estadisticas.registrar_fin_partida(
            db, "JugadorNovato", es_ganador=False,
            comarcas_conquistadas={},
            soldados_matados_en_partida=0
        )

    # ---------------------------------------------------------
    # 3. VERIFICAR CÁLCULOS DEL ESQUEMA
    # ---------------------------------------------------------
    stats_pro = await crud_estadisticas.obtener_estadisticas(db, "JugadorPro")

    pro_schema = EstadisticaRead.model_validate(stats_pro)

    assert pro_schema.winrate == 75.0
    assert pro_schema.comarca_mas_conquistada == nombre_esperado_id_1
    assert pro_schema.num_soldados_matados == 100
    assert pro_schema.conquistas_por_comarca[id_1] == 5

    stats_novato = await crud_estadisticas.obtener_estadisticas(db, "JugadorNovato")
    novato_schema = EstadisticaRead.model_validate(stats_novato)

    assert novato_schema.winrate == 0.0
    assert novato_schema.comarca_mas_conquistada is None

    # ---------------------------------------------------------
    # 4. VERIFICAR EL RANKING GLOBAL
    # ---------------------------------------------------------
    ranking = await crud_estadisticas.obtener_ranking_global(db)
    ranking_nombres = [r.nombre_user for r in ranking if r.nombre_user in ["JugadorPro", "JugadorMedio", "JugadorNovato"]]

    assert ranking_nombres[0] == "JugadorPro"   # 3 Victorias
    assert ranking_nombres[1] == "JugadorMedio" # 1 Victoria
    assert ranking_nombres[2] == "JugadorNovato" # 0 Victorias
