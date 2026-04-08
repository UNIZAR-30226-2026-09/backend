import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.usuario import User, Amistad, EstadoAmistad
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
    # Simulamos que Messi se conecta y Cristiano debería recibir el aviso
    # -------------------------------------------------------------------
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
        async def send_json(self, data):
            self.sent_messages.append(data)
        async def accept(self): pass

    ws_cristiano = MockWebSocket()
    # Simulamos que Cristiano ya está online en el canal global
    await manager.connect_global(ws_cristiano, "Cristiano")

    # Acción: Messi entra al juego (esto es lo que hace tu endpoint global)
    amigos_de_messi = await crud_amigos.obtener_nombres_amigos(db, "Messi")
    for amigo in amigos_de_messi:
        if amigo in manager.global_connections:
            await manager.global_connections[amigo].send_json({
                "tipo_evento": "PRESENCIA",
                "username": "Messi",
                "estado": "online"
            })

    # Verificamos si a Cristiano le ha llegado el mensaje
    assert len(ws_cristiano.sent_messages) > 0
    notificacion = ws_cristiano.sent_messages[0]
    assert notificacion["username"] == "Messi"
    assert notificacion["estado"] == "online"
    print("✅ Sistema de Presencia: Cristiano ha recibido el aviso 'online' de Messi.")

    # -------------------------------------------------------------------
    # 5. ELIMINAR AMIGO
    # Messi elimina a Cristiano (se acabó la rivalidad)
    # -------------------------------------------------------------------
    amistad_obj = await crud_amigos.obtener_relacion_existente(db, "Messi", "Cristiano")
    await crud_amigos.eliminar_amigo(db, amistad_obj)
    
    final_amigos = await crud_amigos.obtener_nombres_amigos(db, "Messi")
    assert "Cristiano" not in final_amigos
    print("✅ Amigo eliminado correctamente. Lista limpia.")

    # Limpiamos manager para otros tests
    manager.disconnect_global("Cristiano")