from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.map_state import map_calculator
from app.core.logica_juego.validaciones import validar_ataque_convencional
from app.core.logica_juego.combate import resolver_ataque_completo
from app.core.logica_juego.maquina_estados import avanzar_fase
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User
from app.db.session import get_db
from app.schemas.combate import AtaqueCreate, ResultadoAtaqueCompleto, MoverConquistaIn, MoverConquistaOut, ColocarTropasIn, PasarFaseOut, ColocarTropasOut, AtaqueEspecialIn, AtaqueEspecialOut
from app.schemas.estado_juego import TerritorioBase, JugadorBase
from app.crud import crud_combates
from app.crud.crud_partidas import obtener_estado_partida, verificar_y_finalizar_partida
from app.crud.crud_logs import registrar_log

from app.core.logica_juego.validaciones import validar_colocacion_tropas
from app.core.logica_juego.combate import resolver_colocacion_tropas, aplicar_resultado_combate, ejecutar_conquista, cobrar_incentivo_ataque
from app.core.logica_juego.ataques_especiales import REGISTRO_ATAQUES
from app.core.logica_juego.utils import obtener_datos_territorio, verificar_movimiento_pendiente
from app.core.logica_juego.victoria import resolver_eliminaciones

from app.core.notifier import notifier


router = APIRouter()

@router.post("/partidas/{partida_id}/ataque", response_model=ResultadoAtaqueCompleto, status_code=status.HTTP_200_OK)
async def ejecutar_ataque(
    partida_id: int,
    ataque_in: AtaqueCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Evalúa y ejecuta un ataque entre territorios, calculando las tiradas de dados y las bajas.

    - **partida_id**: Identificador único de la partida.
    - **ataque_in**: Esquema con los datos del ataque (origen, destino, tropas).
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el resultado matemático y lógico del combate.
    """

    estado_partida = await obtener_estado_partida(db, partida_id)
    atacante_id = usuario_actual.username

    jugador_estado = verificar_movimiento_pendiente(estado_partida.jugadores, atacante_id)

    t_origen = obtener_datos_territorio(estado_partida.mapa, ataque_in.territorio_origen_id)
    t_destino = obtener_datos_territorio(estado_partida.mapa, ataque_in.territorio_destino_id)

    defensor_id = t_destino.owner_id

    try:
        validar_ataque_convencional(
            estado_partida, ataque_in.territorio_origen_id, t_origen,
            ataque_in.territorio_destino_id, t_destino,
            atacante_id, map_calculator
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    era_territorio_vacio = defensor_id == "neutral"
    resultado = resolver_ataque_completo(t_origen.units, t_destino.units)
    resultado.territorio_vacio = era_territorio_vacio

    aplicar_resultado_combate(t_origen, t_destino, resultado)

    bajas_actuales = getattr(jugador_estado, "bajas_causadas", 0)
    jugador_estado.bajas_causadas = getattr(jugador_estado, "bajas_causadas", 0) + resultado.bajas_defensor    
    if resultado.victoria_atacante:
        ejecutar_conquista(t_destino, jugador_estado, atacante_id, 
                          ataque_in.territorio_origen_id, 
                          ataque_in.territorio_destino_id,
                          bajas_defensor_en_combate=resultado.bajas_defensor)
        
        if getattr(t_destino, "estado_bloqueo", None) is not None:
            # Quitamos el bloqueo al territorio
            t_destino.estado_bloqueo = None
            
            # Le quitamos el proyecto al jugador que ha sido derrotado
            if defensor_id in estado_partida.jugadores:
                defensor_dict = estado_partida.jugadores[defensor_id]
                
                if defensor_dict.get("territorio_trabajando") == ataque_in.territorio_destino_id:
                    defensor_dict["territorio_trabajando"] = None
                    
                if defensor_dict.get("territorio_investigando") == ataque_in.territorio_destino_id:
                    defensor_dict["territorio_investigando"] = None
                    defensor_dict["habilidad_investigando"] = None

    cobrar_incentivo_ataque(jugador_estado)

    estado_partida.mapa[ataque_in.territorio_origen_id] = t_origen.model_dump()
    estado_partida.mapa[ataque_in.territorio_destino_id] = t_destino.model_dump()
    estado_partida.jugadores[atacante_id] = jugador_estado.model_dump()

    await crud_combates.guardar_estado_partida(db, estado_partida)

    await registrar_log(
        db=db,
        partida_id=partida_id,
        turno_numero=estado_partida.turno_actual,
        fase=estado_partida.fase_actual.value,
        tipo_evento="ataque_convencional",
        user=atacante_id,
        datos={
            "origen": ataque_in.territorio_origen_id,
            "destino": ataque_in.territorio_destino_id,
            "defensor": defensor_id,
            "bajas_atacante": resultado.bajas_atacante,
            "bajas_defensor": resultado.bajas_defensor,
            "victoria": resultado.victoria_atacante,
        },
    )    

    if resultado.victoria_atacante:

        await registrar_log(
            db=db,
            partida_id=partida_id,
            turno_numero=estado_partida.turno_actual,
            fase=estado_partida.fase_actual.value,
            tipo_evento="conquista",
            user=atacante_id,
            datos={
                "territorio_conquistado": ataque_in.territorio_destino_id,
                "anterior_dueno": defensor_id,
            },
        )

        if not era_territorio_vacio:
            await resolver_eliminaciones(
                db=db,
                partida_id=partida_id,
                defensores={defensor_id},
                mapa=estado_partida.mapa,
                turno_actual=estado_partida.turno_actual,
                fase_actual=estado_partida.fase_actual.value,
                atacante_id=atacante_id,
            )


    await notifier.enviar_resultado_ataque(
        partida_id, 
        ataque_in.territorio_origen_id, 
        ataque_in.territorio_destino_id, 
        resultado
    )
    return resultado


@router.post("/partidas/{partida_id}/mover_conquista", response_model=MoverConquistaOut, status_code=status.HTTP_200_OK)
async def mover_tropas_conquista(
    partida_id: int,
    datos: MoverConquistaIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    
    """
    Ejecuta el movimiento obligatorio de tropas hacia un territorio recientemente conquistado.

    - **partida_id**: Identificador único de la partida.
    - **datos**: Esquema con el número de tropas a movilizar.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un mensaje de confirmación de la operación.
    """
    
    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    
    datos_jugador_dict = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)

    if not jugador_estado.movimiento_conquista_pendiente:
        raise HTTPException(400, "No has conquistado nada recientemente")

    origen_id = jugador_estado.origen_conquista
    destino_id = jugador_estado.destino_conquista

    t_origen = obtener_datos_territorio(estado_partida.mapa, origen_id)
    t_destino = obtener_datos_territorio(estado_partida.mapa, destino_id)

    if t_origen.units <= datos.tropas:
        raise HTTPException(400, "Tienes que dejar al menos 1 guarnición en el territorio de origen")

    # Movemos los monigotes
    t_origen.units -= datos.tropas
    t_destino.units += datos.tropas

    # Limpiamos el chivato de conquista
    jugador_estado.movimiento_conquista_pendiente = False
    jugador_estado.origen_conquista = None
    jugador_estado.destino_conquista = None

    estado_partida.mapa[origen_id] = t_origen.model_dump()
    estado_partida.mapa[destino_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()

    await crud_combates.guardar_estado_partida(db, estado_partida)

    # Avisamos al front
    await notifier.enviar_movimiento_conquista(
        partida_id, origen_id, destino_id, datos.tropas, jugador_id
    )

    return {"mensaje": f"Has movilizado {datos.tropas} tropas a tu nuevo territorio"}


@router.post("/partidas/{partida_id}/pasar_fase", response_model=PasarFaseOut, status_code=status.HTTP_200_OK)
async def pasar_fase_manual(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    
    """
    Avanza manualmente la fase actual del turno del jugador (ej. de Refuerzo a Combate).

    - **partida_id**: Identificador único de la partida.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna la información actualizada de la nueva fase y a quién corresponde el turno.
    """
    estado_partida = await obtener_estado_partida(db, partida_id)
    
    if estado_partida.user_turno_actual != usuario_actual.username:
        raise HTTPException(403, "Quieto ahí, no es tu turno")

    try:
        nuevo_estado = await avanzar_fase(partida_id, db, estado_partida.fase_actual)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))    
    
    if not nuevo_estado:
        raise HTTPException(400, "Error al avanzar la fase")

    return {
        "mensaje": "Fase completada", 
        "nueva_fase": nuevo_estado.fase_actual.value,
        "turno_de": nuevo_estado.user_turno_actual
    }


@router.post("/partidas/{partida_id}/colocar_tropas", response_model=ColocarTropasOut, status_code=status.HTTP_200_OK)
async def colocar_tropas_reserva(
    partida_id: int,
    datos: ColocarTropasIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Permite al jugador en turno desplegar tropas de su reserva en un territorio controlado.

    - **partida_id**: Identificador único de la partida.
    - **datos**: Esquema con el territorio de destino y la cantidad de tropas.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un estado indicando el éxito del despliegue y la reserva restante.
    """

    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    
    t_destino = obtener_datos_territorio(estado_partida.mapa, datos.territorio_id)
    datos_jugador_dict = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)

    try:
        validar_colocacion_tropas(
            estado_partida, jugador_id, datos.territorio_id, 
            t_destino, datos.tropas, jugador_estado.tropas_reserva
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    es_conquista_neutral = t_destino.owner_id == "neutral"

    await resolver_colocacion_tropas(
        jugador_estado, 
        t_destino, 
        datos.tropas, 
        data_territorio=estado_partida.mapa[datos.territorio_id],
        jugadores_estado=estado_partida.jugadores,
        partida_id=partida_id
    )

    if es_conquista_neutral:
        t_destino.owner_id = jugador_id

    estado_partida.mapa[datos.territorio_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()
    await crud_combates.guardar_estado_partida(db, estado_partida)

    await notifier.enviar_tropas_colocadas(
        partida_id, jugador_id, datos.territorio_id, datos.tropas, t_destino.units
    )

    if es_conquista_neutral:
        await notifier.enviar_actualizacion_territorio(
            partida_id=partida_id,
            territorio_id=datos.territorio_id,
            data_territorio=estado_partida.mapa[datos.territorio_id]
        )

    return {
        "mensaje": f"Has metido {datos.tropas} soldados en {datos.territorio_id}",
        "reserva_restante": jugador_estado.tropas_reserva
    }


@router.post("/partidas/{partida_id}/ataque_especial", response_model=AtaqueEspecialOut,status_code=status.HTTP_200_OK)
async def ejecutar_ataque_especial(
    partida_id: int,
    ataque_in: AtaqueEspecialIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Ejecuta un ataque de guerra tecnológica o biológica (Mortero, Misil, Virus, etc.)
    """
    estado_partida = await obtener_estado_partida(db, partida_id)
    atacante_id = usuario_actual.username

    # Es su turno ¿?
    if estado_partida.user_turno_actual != atacante_id:
        raise HTTPException(403, "No puedes lanzar ataques fuera de tu turno")

    # Tiene ese ataque ¿?
    jugador = estado_partida.jugadores.get(atacante_id)
    if not jugador:
        raise HTTPException(404, "Jugador no encontrado en la partida")
    tecnologias_compradas = jugador.get("tecnologias_compradas", [])
    if ataque_in.tipo_ataque not in tecnologias_compradas:
        raise HTTPException(400, f"No has desarrollado la tecnología: {ataque_in.tipo_ataque}")

    funcion_ataque = REGISTRO_ATAQUES.get(ataque_in.tipo_ataque)
    if not funcion_ataque:
        raise HTTPException(400, "Arma o tecnología desconocida")

    if jugador.get("ha_lanzado_especial", False):
        raise HTTPException(
            status_code=400, detail="Solo puedes realizar un ataque especial por turno.")

    propietarios_antes = {
        tid: data["owner_id"]
        for tid, data in estado_partida.mapa.items()
        if data["owner_id"] not in ("neutral", atacante_id)
    }

    try:
        # Ejecutamos el ataque
        resultado_accion = funcion_ataque(estado_partida, atacante_id, ataque_in.origen, ataque_in.destino)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Ya no puedes volver a usar la tecnologia hasta que no la compres otra vez
    jugador["tecnologias_compradas"].remove(ataque_in.tipo_ataque)
    jugador["ha_lanzado_especial"] = True
    flag_modified(estado_partida, "mapa")
    flag_modified(estado_partida, "jugadores")
    await crud_combates.guardar_estado_partida(db, estado_partida)

    # Comprobar si algún territorio enemigo pasó a neutral (tropas a 0)
    posibles_defensores = {
        owner
        for tid, owner in propietarios_antes.items()
        if estado_partida.mapa[tid]["owner_id"] == "neutral"
    }
    
    if posibles_defensores:
        await resolver_eliminaciones(
            db=db,
            partida_id=partida_id,
            defensores=posibles_defensores,
            mapa=estado_partida.mapa,
            turno_actual=estado_partida.turno_actual,
            fase_actual=estado_partida.fase_actual.value,
            atacante_id=atacante_id,
        )

    await registrar_log(
        db=db,
        partida_id=partida_id,
        turno_numero=estado_partida.turno_actual,
        fase=estado_partida.fase_actual.value,
        tipo_evento="ataque_especial",
        user=atacante_id,
        datos={
            "tipo_ataque": ataque_in.tipo_ataque,
            "origen": ataque_in.origen,
            "destino": ataque_in.destino,
        },
    )

    # Notificar al resto de la partida
    await notifier.enviar_ataque_especial(
        partida_id=partida_id, 
        atacante_id=atacante_id, 
        tipo_ataque=ataque_in.tipo_ataque, 
        origen_id=ataque_in.origen, 
        destino_id=ataque_in.destino,
        resultado=resultado_accion
    )

    return AtaqueEspecialOut(
        mensaje=f"Has lanzado {ataque_in.tipo_ataque} sobre {ataque_in.destino} con éxito.",
        tipo_ataque=ataque_in.tipo_ataque,
        destino=ataque_in.destino
    )