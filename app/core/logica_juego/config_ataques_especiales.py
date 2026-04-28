# Nombres efectos
class TipoEfecto:
    # Guerra biológica
    GRIPE_AVIAR = "gripe_aviar"
    CORONAVIRUS = "coronavirus"
    FATIGA = "fatiga"

    # Operaciones y Logística
    INHIBIDOR_SENAL = "inhibidor_senal"
    PROPAGANDA = "propaganda"
    MURO = "muro"
    SANCIONES = "sanciones"

# Nombres ataques
class TipoAtaque:
    # Artilleria
    MORTERO_TACTICO = "mortero_tactico"
    MISIL_CRUCERO = "misil_crucero"
    CABEZA_NUCLEAR = "cabeza_nuclear"
    BOMBA_RACIMO = "bomba_racimo"

    # Guerra biológica
    GRIPE_AVIAR = "gripe_aviar"
    VACUNA_UNIVERSAL = "vacuna_universal"
    FATIGA = "fatiga"
    CORONAVIRUS = "coronavirus"

    # Operaciones y Logística
    ACADEMIA_MILITAR = "academia_militar"
    INHIBIDOR_SENAL = "inhibidor_senal"
    MURO_FRONTERIZO = "muro_fronterizo"
    PROPAGANDA_SUBVERSIVA = "propaganda_subversiva"
    SANCIONES_INTERNACIONALES = "sanciones_internacionales"

# Valores para balancear el juego
CONFIG_ATAQUES = {
    # Artilleria
    TipoAtaque.MORTERO_TACTICO: {
        "rango": 2,
        "dano_min": 1,
        "dano_max": 4
    },
    TipoAtaque.MISIL_CRUCERO: {
        "rango": 3,
        "dano_porcentaje": 0.30
    },
    TipoAtaque.CABEZA_NUCLEAR: {
        "rango": 3,
        "dano_fijo": 10
    },
    TipoAtaque.BOMBA_RACIMO: {
        "rango": 3,
        "dano_fijo_objetivo": 10,
        "dano_colindantes": 0.30
    },

    # Guerra biologica
    TipoAtaque.GRIPE_AVIAR: {
        "rondas_duracion": 3,
        "dano_por_turno": 1
    },
    TipoAtaque.VACUNA_UNIVERSAL: {
        "enfermedades_curables": [TipoEfecto.GRIPE_AVIAR, TipoEfecto.CORONAVIRUS, TipoEfecto.FATIGA]
    },
    TipoAtaque.CORONAVIRUS: {
        "rango": 1,
        "dano_inicial": 0.40,
        "dano_recurrente": 0.10,
        "rondas_duracion": 2,
        "probabilidad_expansion": 0.25
    },
    TipoAtaque.FATIGA: {
        "rango": 3,
        "rondas_duracion": 2
    },

    # Operaciones y Logistica
    TipoAtaque.ACADEMIA_MILITAR: {
        # Define el multiplicador de tropas
        "multiplicador_tropas": 1.50
    },
    TipoAtaque.INHIBIDOR_SENAL: {
        "rango": 2,
        "rondas_duracion": 1
    },
    TipoAtaque.MURO_FRONTERIZO: {
        "rango": 1,
        "rondas_duracion": 1
    },
    TipoAtaque.PROPAGANDA_SUBVERSIVA: {
        "rondas_duracion": 2,
        "robo_porcentaje": 0.50
    },
    TipoAtaque.SANCIONES_INTERNACIONALES: {
        # Se lanza a un jugador, no a un territorio.
        "rondas_duracion": 1
    }
}