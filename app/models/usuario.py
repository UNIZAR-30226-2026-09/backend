from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer, Enum, CheckConstraint, JSON
from app.db.base import Base
import enum
from typing import List

# ----------------------------------------------------------------------------
# AUXILIARES
# ----------------------------------------------------------------------------

class EstadoAmistad(str, enum.Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"

# ----------------------------------------------------------------------------
# PRINCIPALES
# ----------------------------------------------------------------------------

class User(Base):
    __tablename__ = "usuarios"

    username: Mapped[str] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    passwd_hash: Mapped[str] = mapped_column(String(255))
    #avatar: Mapped[str] = mapped_column(String(255), default="default_avatar.png", nullable=True)
    #fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # --- RELACIONES ---    
    estadisticas: Mapped["Estadistica"] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    amistades_enviadas: Mapped[List["Amistad"]] = relationship("Amistad", foreign_keys="[Amistad.user_1]", back_populates="usuario_1", cascade="all, delete-orphan")
    amistades_recibidas: Mapped[List["Amistad"]] = relationship( "Amistad", foreign_keys="[Amistad.user_2]", back_populates="usuario_2", cascade="all, delete-orphan")


class Estadistica(Base):
    __tablename__ = "estadisticas"

    nombre_user: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="CASCADE"), primary_key=True)
    num_partidas_jugadas: Mapped[int] = mapped_column(Integer, default=0)
    num_partidas_ganadas: Mapped[int] = mapped_column(Integer, default=0)
    num_regiones_conquistadas: Mapped[int] = mapped_column(Integer, default=0)
    num_soldados_matados: Mapped[int] = mapped_column(Integer, default=0)
    conquistas_por_region: Mapped[dict] = mapped_column(JSON, default=dict)

    # CONDICIONES
    __table_args__ = (
        CheckConstraint('num_partidas_jugadas >= 0', name='check_partidas_jugadas_positivas'),
        CheckConstraint('num_partidas_ganadas >= 0', name='check_partidas_ganadas_positivas'),
        CheckConstraint('num_regiones_conquistadas >= 0', name='check_regiones_positivas'),
        CheckConstraint('num_soldados_matados >= 0', name='check_tropas_positivas'),
    )

    # --- RELACIONES ---    
    usuario: Mapped["User"] = relationship(back_populates="estadisticas")


class Amistad(Base):
    __tablename__ = "amistades"

    user_1: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="CASCADE"), primary_key=True)
    user_2: Mapped[str] = mapped_column(ForeignKey("usuarios.username", ondelete="CASCADE"), primary_key=True)
    
    estado: Mapped[EstadoAmistad] = mapped_column(
        Enum(EstadoAmistad, name="estado_amistad_enum", create_constraint=True), 
        default=EstadoAmistad.PENDIENTE,
        nullable=False
    )

    usuario_1: Mapped["User"] = relationship("User", foreign_keys=[user_1], back_populates="amistades_enviadas")
    usuario_2: Mapped["User"] = relationship("User", foreign_keys=[user_2], back_populates="amistades_recibidas")