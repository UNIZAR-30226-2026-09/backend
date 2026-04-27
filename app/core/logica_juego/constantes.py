from app.core.logica_juego.config_ataques_especiales import TipoAtaque, CONFIG_ATAQUES

_c = CONFIG_ATAQUES

HABILIDADES = {
    # Biológica
    TipoAtaque.GRIPE_AVIAR: {
        "nombre": "Gripe Aviar",
        "descripcion": (
            f"Infecta un territorio enemigo. Resta {_c[TipoAtaque.GRIPE_AVIAR]['dano_por_turno']} tropas "
            f"por turno durante {_c[TipoAtaque.GRIPE_AVIAR]['duracion']} rondas al inicio del refuerzo "
            f"del afectado. Si llega a 0 tropas, el territorio pasa a neutral."
        ),
        "precio": 500,
        "rama": "biologica",
        "nivel": 1,
    },
    TipoAtaque.VACUNA_UNIVERSAL: {
        "nombre": "Vacuna Universal",
        "descripcion": (
            "Defensa sanitaria sobre territorio propio. Elimina Gripe Aviar, Coronavirus y Fatiga "
            "en la red de territorios propios conectados."
        ),
        "precio": 1000,
        "rama": "biologica",
        "nivel": 2,
    },
    TipoAtaque.FATIGA: {
        "nombre": "Fatiga",
        "descripcion": (
            f"Sabotaje de hasta {_c[TipoAtaque.FATIGA]['rango']} saltos. Bloquea la generación de "
            f"dinero e investigación del territorio durante {_c[TipoAtaque.FATIGA]['duracion']} rondas. "
            f"No se acumula sobre fatiga activa."
        ),
        "precio": 1000,
        "rama": "biologica",
        "nivel": 2,
    },
    TipoAtaque.CORONAVIRUS: {
        "nombre": "Coronavirus",
        "descripcion": (
            f"Impacto inicial del {int(_c[TipoAtaque.CORONAVIRUS]['dano_inicial'] * 100)}% y daño "
            f"recurrente del {int(_c[TipoAtaque.CORONAVIRUS]['dano_recurrente'] * 100)}% por turno. "
            f"Se expande a vecinos con un {int(_c[TipoAtaque.CORONAVIRUS]['probabilidad_expansion'] * 100)}% "
            f"de probabilidad al final de ronda. Dura {_c[TipoAtaque.CORONAVIRUS]['rondas_duracion']} rondas por jugador."
        ),
        "precio": 2500,
        "rama": "biologica",
        "nivel": 3,
    },

    # Logistica
    TipoAtaque.ACADEMIA_MILITAR: {
        "nombre": "Academia Militar",
        "descripcion": (
            f"Pasiva permanente. Multiplica ×{_c[TipoAtaque.ACADEMIA_MILITAR]['multiplicador_tropas']} "
            f"(redondeado arriba) los refuerzos al inicio del turno. "
            f"Si ese turno recibes Sanciones Internacionales, el bono no se aplica y recibes 0 refuerzos."
        ),
        "precio": 500,
        "rama": "logistica",
        "nivel": 1,
    },
    TipoAtaque.INHIBIDOR_SENAL: {
        "nombre": "Inhibidor de Señal",
        "descripcion": (
            f"Control táctico de hasta {_c[TipoAtaque.INHIBIDOR_SENAL]['rango']} saltos. Bloquea los "
            f"ataques convencionales desde el territorio afectado durante "
            f"{_c[TipoAtaque.INHIBIDOR_SENAL]['duracion']} turno."
        ),
        "precio": 1000,
        "rama": "logistica",
        "nivel": 2,
    },
    TipoAtaque.PROPAGANDA_SUBVERSIVA: {
        "nombre": "Propaganda Subversiva",
        "descripcion": (
            f"Sabotaje sobre jugador enemigo. Roba el "
            f"{int(_c[TipoAtaque.PROPAGANDA_SUBVERSIVA]['robo_porcentaje'] * 100)}% de sus refuerzos "
            f"calculados y los transfiere al atacante. Dura "
            f"{_c[TipoAtaque.PROPAGANDA_SUBVERSIVA]['duracion']} turnos de la víctima."
        ),
        "precio": 1000,
        "rama": "logistica",
        "nivel": 2,
    },
    TipoAtaque.MURO_FRONTERIZO: {
        "nombre": "Muro Fronterizo",
        "descripcion": (
            f"Defensa fronteriza de rango exacto {_c[TipoAtaque.MURO_FRONTERIZO]['rango']} salto. "
            f"Sella la frontera en ambos sentidos durante {_c[TipoAtaque.MURO_FRONTERIZO]['duracion']} turno. "
            f"No bloquea la fortificación propia."
        ),
        "precio": 1500,
        "rama": "logistica",
        "nivel": 3,
    },
    TipoAtaque.SANCIONES_INTERNACIONALES: {
        "nombre": "Sanciones Internacionales",
        "descripcion": (
            f"Ataque económico sobre jugador enemigo. Su siguiente refuerzo pasa a 0 tropas con "
            f"prioridad sobre Academia y Propaganda. Dura "
            f"{_c[TipoAtaque.SANCIONES_INTERNACIONALES]['duracion']} turno."
        ),
        "precio": 2500,
        "rama": "logistica",
        "nivel": 3,
    },

    # Artillería
    TipoAtaque.MORTERO_TACTICO: {
        "nombre": "Mortero Táctico",
        "descripcion": (
            f"Artillería de rango exacto {_c[TipoAtaque.MORTERO_TACTICO]['rango']} saltos. "
            f"Inflige entre {_c[TipoAtaque.MORTERO_TACTICO]['dano_min']} y "
            f"{_c[TipoAtaque.MORTERO_TACTICO]['dano_max']} bajas aleatorias. "
            f"No alcanza territorios adyacentes."
        ),
        "precio": 500,
        "rama": "artilleria",
        "nivel": 1,
    },
    TipoAtaque.MISIL_CRUCERO: {
        "nombre": "Misil Crucero",
        "descripcion": (
            f"Ataque de precisión de hasta {_c[TipoAtaque.MISIL_CRUCERO]['rango']} saltos. "
            f"Inflige el {int(_c[TipoAtaque.MISIL_CRUCERO]['dano_porcentaje'] * 100)}% de las tropas "
            f"del territorio objetivo."
        ),
        "precio": 1500,
        "rama": "artilleria",
        "nivel": 2,
    },
    TipoAtaque.CABEZA_NUCLEAR: {
        "nombre": "Cabeza Nuclear",
        "descripcion": (
            f"Destrucción masiva de hasta {_c[TipoAtaque.CABEZA_NUCLEAR]['rango']} saltos. "
            f"Inflige {_c[TipoAtaque.CABEZA_NUCLEAR]['dano_fijo']} bajas fijas al territorio objetivo."
        ),
        "precio": 3000,
        "rama": "artilleria",
        "nivel": 3,
    },
    TipoAtaque.BOMBA_RACIMO: {
        "nombre": "Bomba de Racimo",
        "descripcion": (
            f"Daño de área de hasta {_c[TipoAtaque.BOMBA_RACIMO]['rango']} saltos. "
            f"{_c[TipoAtaque.BOMBA_RACIMO]['dano_fijo_objetivo']} bajas fijas al objetivo y "
            f"{int(_c[TipoAtaque.BOMBA_RACIMO]['dano_colindantes'] * 100)}% de bajas a todos los "
            f"territorios colindantes, incluidos los propios."
        ),
        "precio": 2000,
        "rama": "artilleria",
        "nivel": 3,
    },
}

# Estructura de progresión (prerequisitos y desbloqueos)
ARBOL_TECNOLOGICO = {
    # Biológica — rombo
    TipoAtaque.GRIPE_AVIAR: {
        "prerequisito": None,
        "desbloquea": [TipoAtaque.VACUNA_UNIVERSAL, TipoAtaque.FATIGA]
    },
    TipoAtaque.VACUNA_UNIVERSAL: {
        "prerequisito": TipoAtaque.GRIPE_AVIAR,
        "desbloquea": [TipoAtaque.CORONAVIRUS]
    },
    TipoAtaque.FATIGA: {
        "prerequisito": TipoAtaque.GRIPE_AVIAR,
        "desbloquea": [TipoAtaque.CORONAVIRUS]
    },
    TipoAtaque.CORONAVIRUS: {
        "prerequisito": [TipoAtaque.VACUNA_UNIVERSAL, TipoAtaque.FATIGA],
        "desbloquea": []
    },

    # Logística — Y
    TipoAtaque.ACADEMIA_MILITAR: {
        "prerequisito": None,
        "desbloquea": [TipoAtaque.INHIBIDOR_SENAL, TipoAtaque.PROPAGANDA_SUBVERSIVA]
    },
    TipoAtaque.INHIBIDOR_SENAL: {
        "prerequisito": TipoAtaque.ACADEMIA_MILITAR,
        "desbloquea": [TipoAtaque.MURO_FRONTERIZO]
    },
    TipoAtaque.PROPAGANDA_SUBVERSIVA: {
        "prerequisito": TipoAtaque.ACADEMIA_MILITAR,
        "desbloquea": [TipoAtaque.SANCIONES_INTERNACIONALES]
    },
    TipoAtaque.MURO_FRONTERIZO: {
        "prerequisito": TipoAtaque.INHIBIDOR_SENAL,
        "desbloquea": []
    },
    TipoAtaque.SANCIONES_INTERNACIONALES: {
        "prerequisito": TipoAtaque.PROPAGANDA_SUBVERSIVA,
        "desbloquea": []
    },

    # Artillería — elección final
    TipoAtaque.MORTERO_TACTICO: {
        "prerequisito": None,
        "desbloquea": [TipoAtaque.MISIL_CRUCERO]
    },
    TipoAtaque.MISIL_CRUCERO: {
        "prerequisito": TipoAtaque.MORTERO_TACTICO,
        "desbloquea": [TipoAtaque.CABEZA_NUCLEAR, TipoAtaque.BOMBA_RACIMO]
    },
    TipoAtaque.CABEZA_NUCLEAR: {
        "prerequisito": TipoAtaque.MISIL_CRUCERO,
        "desbloquea": []
    },
    TipoAtaque.BOMBA_RACIMO: {
        "prerequisito": TipoAtaque.MISIL_CRUCERO,
        "desbloquea": []
    }
}

AVATARES_PERMITIDOS = [
    "1.png",
    "2.png",
    "3.png",
    "4.png",
    "5.png",
    "6.png"
]

MENSAJES_CHAT_PERMITIDOS = [
    "¡Buena jugada!",
    "¡Maldición!",
    "¿Hacemos una alianza?",
    "¡A por él!",
    "¡Me rindo!",
    "Necesito refuerzos..."
]

REACCIONES_CHAT_PERMITIDAS = [
    "1.png",
    "2.png",
    "3.png",
    "4.png",
    "5.png",
    "6.png"  
]