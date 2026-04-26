from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer, Enum, CheckConstraint, JSON, func
from app.db.base import Base
import enum
from sqlalchemy.dialects.postgresql import JSONB

from datetime import datetime
from sqlalchemy import DateTime
from typing import List

# ----------------------------------------------------------------------------
# AUXILIARES
# ----------------------------------------------------------------------------

class TipoVisibilidad(str, enum.Enum):
    PUBLICA = "publica"
    PRIVADA = "privada"

class EstadosPartida(str, enum.Enum):
    CREANDO = "creando"
    ACTIVA = "activa"
    PAUSADA = "pausada"
    FINALIZADA = "finalizada"
    
class EstadoJugador(str, enum.Enum):
    VIVO = "vivo"
    MUERTO = "muerto"
    
class FasePartida(str, enum.Enum):
    REFUERZO = "refuerzo"
    GESTION = "gestion"
    ATAQUE_CONVENCIONAL = "ataque_convencional"
    ATAQUE_ESPECIAL = "ataque_especial"
    FORTIFICACION = "fortificacion"

# ----------------------------------------------------------------------------
# PRINCIPALES
# ----------------------------------------------------------------------------

class Partida(Base):
    __tablename__ = "partidas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    config_max_players: Mapped[int] = mapped_column(Integer, default=4)

    # La partida puede ser publica o privada 
    config_visibility: Mapped[TipoVisibilidad] = mapped_column(
        Enum(TipoVisibilidad, name="tipo_visibilidad_enum", create_constraint=True), 
        default=TipoVisibilidad.PUBLICA
    )

    codigo_invitacion: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    config_timer_seconds: Mapped[int] = mapped_column(Integer, default=60)
    #fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Estados: creando, activa, pausada, finalizada
    estado: Mapped[EstadosPartida] = mapped_column(
        Enum(EstadosPartida, name="estado_partida_enum", create_constraint=True), 
        default=EstadosPartida.CREANDO
    )
    
    # Permitimos que sea NULL
    ganador: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="SET NULL"), nullable=True)

    creador: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="SET NULL"), nullable=False)

    __table_args__ = (
        CheckConstraint('config_max_players >= 2 AND config_max_players <= 4', name='check_max_players_valido'),
        CheckConstraint('config_timer_seconds > 0', name='check_timer_valido'),
    )

    # Back_populates: "partida" tiene que existir en "EstadoPartida"
    # Cascade all: si guardas o actualizas "Partida" tmb se actualiza el estado
    # Cascade delete-orphan: si borras "Partida" tmb se borra el estado
    estado_juego: Mapped["EstadoPartida"] = relationship(back_populates="partida", cascade="all, delete-orphan")
    jugadores_en_sala: Mapped[List["JugadoresPartida"]] = relationship(back_populates="partida_asociada")



class JugadoresPartida(Base):

    __tablename__ = "jugadores_partida"

    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="CASCADE"), primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id", ondelete="CASCADE"), primary_key=True)

    # Orden de juego de este jugador
    turno: Mapped[int] = mapped_column(Integer) 

    estado_jugador: Mapped[EstadoJugador] = mapped_column(
        Enum(EstadoJugador, name="estado_jugador_enum", create_constraint=True),
        default=EstadoJugador.VIVO
    )

    partida_asociada: Mapped["Partida"] = relationship(back_populates="jugadores_en_sala")


class EstadoPartida(Base):

    __tablename__ = "estado_partida"

    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id", ondelete="CASCADE"), primary_key=True)
    
    fase_actual: Mapped[FasePartida] = mapped_column(
        Enum(FasePartida, name="fase_partida_enum", create_constraint=True),
        default=FasePartida.REFUERZO,
        nullable=False
    )    

    # Hora en UTC
    fin_fase_actual: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Restrict no permite que se borre
    user_turno_actual: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="RESTRICT"), nullable=False)
    turno_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # JSONB
    mapa: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    jugadores: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    
    partida: Mapped["Partida"] = relationship(back_populates="estado_juego")


class LogPartida(Base):

    __tablename__ = "logs_partida"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id", ondelete="CASCADE"), index=True)
    turno_numero: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fase: Mapped[str] = mapped_column(String(50), nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    
    user: Mapped[str] = mapped_column(String(100), nullable=True)
    datos: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)