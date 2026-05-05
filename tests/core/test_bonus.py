import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.partida import EstadoPartida
from app.core.logica_juego.maquina_estados import asignar_tropas_reserva

@pytest.mark.asyncio
async def test_asignar_tropas_reserva_bonus_regiones():
    # ---------------------------------------------------------
    # 1. SETUP DEL ESTADO DE LA PARTIDA
    # ---------------------------------------------------------
    mapa_simulado = {
        "T1": {"owner_id": "Jugador1", "units": 1},
        "T2": {"owner_id": "Jugador1", "units": 1},
        "T3": {"owner_id": "Jugador1", "units": 1},
        "T4": {"owner_id": "Enemigo", "units": 1},
    }

    jugadores_simulados = {
        "Jugador1": {"tropas_reserva": 0, "efectos": [], "tecnologias_compradas": [], "ha_fortificado": False},
        "Enemigo": {"tropas_reserva": 0, "efectos": [], "tecnologias_compradas": [], "ha_fortificado": False}
    }

    estado_mock = EstadoPartida(
        partida_id=99,
        user_turno_actual="Jugador1",
        mapa=mapa_simulado,
        jugadores=jugadores_simulados,
        fin_fase_actual=datetime.now(timezone.utc)
    )

    db_mock = AsyncMock() # Simulamos la base de datos para que no intente guardar de verdad

    # ---------------------------------------------------------
    # 2. SIMULAR EL MAPA DE ARAGÓN (MOCKS)
    # ---------------------------------------------------------
    class RegionMock:
        def __init__(self, name, comarcas, bonus_troops=0):
            self.name = name
            self.comarcas = comarcas
            self.bonus_troops = bonus_troops

    regiones_falsas = {
        "region_a": RegionMock("Región A", ["T1", "T2"], bonus_troops=2),
        
        "region_b": RegionMock("Región B", ["T3", "T4"], bonus_troops=3)
    }

    # ---------------------------------------------------------
    # 3. EJECUTAR LA FUNCIÓN INTERCEPTANDO DEPENDENCIAS
    # ---------------------------------------------------------
    with patch('app.core.logica_juego.maquina_estados.game_map_state') as mock_mapa:
        mock_mapa.regions = regiones_falsas
        
        with patch('app.core.logica_juego.maquina_estados.notifier.enviar_cambio_fase', new_callable=AsyncMock), \
             patch('app.core.logica_juego.maquina_estados.actualizar_tropas_reserva', new_callable=AsyncMock):
            
            tropas_totales = await asignar_tropas_reserva(estado_mock, db_mock)

    # ---------------------------------------------------------
    # 4. VERIFICAR EL RESULTADO MATEMÁTICO
    # ---------------------------------------------------------
    tropas, _ = tropas_totales
    assert tropas == 5, f"Error: Se esperaban 5 tropas, pero calculó {tropas}"
    
    print("\n✅ Test de Bonus por Región superado: ¡Las matemáticas no fallan!")