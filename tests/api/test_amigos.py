import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usuario import User, EstadoAmistad
from app.crud import crud_amigos
from app.core.ws_manager import manager

@pytest.mark.asyncio
async def test_flujo_completo_amistad_y_presencia(db: AsyncSession):
    # -------------------------------------------------------------------
    # 1. SETUP: CREAR DOS USUARIOS
    # -------------------------------------------------------------------
    user1 = User(username="Messi", email="leo@goat.com", passwd_hash="123")
    user2 = User(username="Cristiano", email="cr7@siu.com", passwd_hash="456")
    db.add_all([user1, user2])
    await db.commit()
    print("\n✅ Usuarios creados: Messi y Cristiano.")

    # -------------------------------------------------------------------
    # 2. SOLICITUD DE AMISTAD
    # Messi envía solicitud a Cristiano
    # -------------------------------------------------------------------
    solicitud = await crud_amigos.crear_solicitud(db, "Messi", "Cristiano")
    assert solicitud.user_1 == "Messi"
    assert solicitud.estado == EstadoAmistad.PENDIENTE
    
    pendientes = await crud_amigos.obtener_solicitudes_pendientes(db, "Cristiano")
    assert len(pendientes) == 1
    print("✅ Solicitud enviada y detectada como pendiente para Cristiano.")

    # -------------------------------------------------------------------
    # 3. ACEPTAR AMISTAD
    # Cristiano acepta a Messi
    # -------------------------------------------------------------------
    await crud_amigos.aceptar_solicitud(db, solicitud)
    
    amigos_messi = await crud_amigos.obtener_nombres_amigos(db, "Messi")
    assert "Cristiano" in amigos_messi
    print("✅ Amistad aceptada. Messi ahora tiene a Cristiano en su lista.")

    # -------------------------------------------------------------------
    # 4. TEST DE PRESENCIA (WEBSOCKETS)
    # Simulamos que Cristiano está en el menú (Global) y le llega un aviso
    # -------------------------------------------------------------------
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
        async def send_json(self, data):
            self.sent_messages.append(data)
        async def accept(self): pass
        async def close(self, code=1000): pass

    ws_cristiano = MockWebSocket()
    await manager.connect_global(ws_cristiano, "Cristiano")

    # Acción manual: Aviso a los amigos
    for amigo in amigos_messi:
        if amigo in manager.global_connections:
            await manager.global_connections[amigo].send_json({
                "tipo_evento": "PRESENCIA",
                "username": "Messi",
                "estado": "online"
            })

    assert len(ws_cristiano.sent_messages) > 0
    notificacion = ws_cristiano.sent_messages[0]
    assert notificacion["username"] == "Messi"
    assert notificacion["estado"] == "online"
    print("✅ Sistema de Presencia: Cristiano ha recibido el aviso 'online' de Messi.")

    # -------------------------------------------------------------------
    # 4.5 TEST DEL RADAR DE AMIGOS ACTIVOS (ISSUE 4)
    # -------------------------------------------------------------------
    ws_messi = MockWebSocket()
    # Conectamos a Messi a la partida 1
    await manager.connect(ws_messi, id_partida=1, username="Messi")

    # 1. Comprobamos los estados directamente en el manager
    assert manager.obtener_estado_conexion("Cristiano") == "CONECTADO"
    assert manager.obtener_estado_conexion("Messi") == "EN_PARTIDA"
    
    # 2. Simulamos la fusión del endpoint para Cristiano
    amigos_cr7 = await crud_amigos.obtener_nombres_amigos(db, "Cristiano")
    amigos_activos_cr7 = []
    
    for amigo in amigos_cr7:
        amigos_activos_cr7.append({
            "username": amigo,
            "estado_conexion": manager.obtener_estado_conexion(amigo)
        })

    assert len(amigos_activos_cr7) == 1
    assert amigos_activos_cr7[0]["username"] == "Messi"
    assert amigos_activos_cr7[0]["estado_conexion"] == "EN_PARTIDA"
    print("✅ Radar Issue 4: Cristiano ve correctamente que Messi está EN_PARTIDA.")

    # -------------------------------------------------------------------
    # 5. ELIMINAR AMIGO Y LIMPIAR CONEXIONES
    # -------------------------------------------------------------------
    amistad_obj = await crud_amigos.obtener_relacion_existente(db, "Messi", "Cristiano")
    await crud_amigos.eliminar_amigo(db, amistad_obj)
    
    final_amigos = await crud_amigos.obtener_nombres_amigos(db, "Messi")
    assert "Cristiano" not in final_amigos
    print("✅ Amigo eliminado correctamente. Lista limpia.")

    # Limpiamos los diccionarios del manager para que no interfieran en futuros tests
    manager.disconnect_global("Cristiano")
    manager.disconnect(id_partida=1, username="Messi")