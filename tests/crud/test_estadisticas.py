import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usuario import User
from app.crud import crud_estadisticas
from app.schemas.usuario import EstadisticaRead

@pytest.mark.asyncio
async def test_estadisticas_calculos_y_ranking(db: AsyncSession):
    
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
            regiones_conquistadas={"Zaragoza": 1, "Huesca": 1}, 
            soldados_matados_en_partida=20
        )

    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorPro", es_ganador=False, 
        regiones_conquistadas={"Zaragoza": 2}, 
        soldados_matados_en_partida=40
    )

    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorMedio", es_ganador=True, 
        regiones_conquistadas={"Teruel": 3}, 
        soldados_matados_en_partida=150
    )
    await crud_estadisticas.registrar_fin_partida(
        db, "JugadorMedio", es_ganador=False, 
        regiones_conquistadas={}, 
        soldados_matados_en_partida=0
    )

    for _ in range(10):
        await crud_estadisticas.registrar_fin_partida(
            db, "JugadorNovato", es_ganador=False, 
            regiones_conquistadas={}, 
            soldados_matados_en_partida=0
        )

    # ---------------------------------------------------------
    # 3. VERIFICAR CÁLCULOS DEL ESQUEMA
    # ---------------------------------------------------------
    stats_pro = await crud_estadisticas.obtener_estadisticas(db, "JugadorPro")
    
    pro_schema = EstadisticaRead.model_validate(stats_pro)
    
    assert pro_schema.winrate == 75.0
    assert pro_schema.region_favorita == "Zaragoza"
    assert pro_schema.num_soldados_matados == 100
    assert pro_schema.conquistas_por_region["Zaragoza"] == 5

    stats_novato = await crud_estadisticas.obtener_estadisticas(db, "JugadorNovato")
    novato_schema = EstadisticaRead.model_validate(stats_novato)
    
    assert novato_schema.winrate == 0.0
    assert novato_schema.region_favorita is None

    # ---------------------------------------------------------
    # 4. VERIFICAR EL RANKING GLOBAL
    # ---------------------------------------------------------
    ranking = await crud_estadisticas.obtener_ranking_global(db)
    ranking_nombres = [r.nombre_user for r in ranking if r.nombre_user in ["JugadorPro", "JugadorMedio", "JugadorNovato"]]
    
    assert ranking_nombres[0] == "JugadorPro"   # 3 Victorias
    assert ranking_nombres[1] == "JugadorMedio" # 1 Victoria
    assert ranking_nombres[2] == "JugadorNovato" # 0 Victorias

    print("\n✅ ¡Módulo de Estadísticas Validado! El cálculo y el ranking funcionan perfecto.")