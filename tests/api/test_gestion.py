import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.crud_partidas import obtener_estado_partida
from app.crud.crud_combates import guardar_estado_partida
from app.core.logica_juego.maquina_estados import resolver_gestion_ronda
from app.core.logica_juego.constantes import PRECIOS_TECNOLOGIA
from app.models.usuario import User
from app.models.partida import Partida, EstadoPartida, FasePartida

@pytest.mark.asyncio
async def test_fase_gestion_completa(db: AsyncSession):
    # -------------------------------------------------------------------
    # 1. SETUP: PREPARAMOS LA PARTIDA EN FASE DE GESTIÓN
    # -------------------------------------------------------------------
    user = User(username="cientifico_loco", email="test@labs.com", passwd_hash="123")
    db.add(user)
    await db.commit()

    partida = Partida(
        id=99, 
        config_max_players=2, 
        creador="cientifico_loco",
        codigo_invitacion="TEST1234"
    )
    db.add(partida)
    await db.commit()

    estado = EstadoPartida(
        partida_id=99,
        fase_actual=FasePartida.GESTION,
        fin_fase_actual=datetime.now(timezone.utc), # <--- AÑADIDO: Fecha límite obligatoria
        mapa={
            "zaragoza": {"owner_id": "cientifico_loco", "units": 5, "estado_bloqueo": None},
            "huesca": {"owner_id": "cientifico_loco", "units": 10, "estado_bloqueo": None}
        },
        jugadores={
            "cientifico_loco": {
                "monedas": 0,
                "territorio_trabajando": None,
                "territorio_investigando": None,
                "rama_investigando": None,
                "nivel_ramas": {"biologica": 0, "logistica": 0, "artilleria": 0},
                "tecnologias_predesbloqueadas": [],
                "tecnologias_compradas": []
            }
        },
        user_turno_actual="cientifico_loco"
    )
    db.add(estado)
    await db.commit()

    # -------------------------------------------------------------------
    # 2. ACCIÓN: ASIGNAR TRABAJO E INVESTIGACIÓN
    # -------------------------------------------------------------------
    estado_db = await obtener_estado_partida(db, 99)

    estado_db.mapa["huesca"]["estado_bloqueo"] = "trabajando"
    estado_db.jugadores["cientifico_loco"]["territorio_trabajando"] = "huesca"

    estado_db.mapa["zaragoza"]["estado_bloqueo"] = "investigando"
    estado_db.jugadores["cientifico_loco"]["territorio_investigando"] = "zaragoza"
    estado_db.jugadores["cientifico_loco"]["rama_investigando"] = "artilleria"

    await guardar_estado_partida(db, estado_db)

    # -------------------------------------------------------------------
    # 3. EL TIEMPO PASA: RESOLUCIÓN DE LA RONDA
    # -------------------------------------------------------------------
    await resolver_gestion_ronda(estado_db, "cientifico_loco")
    await guardar_estado_partida(db, estado_db)

    estado_actualizado = await obtener_estado_partida(db, 99)
    jugador = estado_actualizado.jugadores["cientifico_loco"]

    # Verificamos Economía
    assert jugador["monedas"] == 1000, "Debería haber ganado 1000 monedas (10 tropas * 100)"
    assert estado_actualizado.mapa["huesca"]["estado_bloqueo"] is None, "Huesca debería estar libre"

    # Verificamos Ciencia
    assert jugador["nivel_ramas"]["artilleria"] == 1, "Debería haber subido al Nivel 1 de artillería"
    assert "mortero_tactico" in jugador["tecnologias_predesbloqueadas"], "Mortero predesbloqueado"
    assert estado_actualizado.mapa["zaragoza"]["estado_bloqueo"] is None, "Zaragoza debería estar libre"
    print("\n✅ Parte 1: Resolución de Trabajo e Investigación perfecta.")

    # -------------------------------------------------------------------
    # 4. COMPRAS: ADQUIRIR TECNOLOGÍA
    # -------------------------------------------------------------------
    precio_mortero = PRECIOS_TECNOLOGIA["mortero_tactico"]
    
    jugador["monedas"] -= precio_mortero
    jugador["tecnologias_compradas"].append("mortero_tactico")
    await guardar_estado_partida(db, estado_actualizado)

    estado_final = await obtener_estado_partida(db, 99)
    jug_final = estado_final.jugadores["cientifico_loco"]

    assert jug_final["monedas"] == 500, "Deberían quedar 500 monedas (1000 - 500)"
    assert "mortero_tactico" in jug_final["tecnologias_compradas"], "Compra registrada en la BD"
    print("✅ Parte 2: Compra de tecnología validada con éxito.")