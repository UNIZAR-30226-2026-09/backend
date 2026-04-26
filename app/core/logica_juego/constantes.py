from app.core.logica_juego.config_ataques_especiales import TipoAtaque

HABILIDADES = {
    # Biológica
    TipoAtaque.GRIPE_AVIAR: {
        "nombre": "Gripe Aviar",
        "descripcion": "Descripcion 1",
        "precio": 500,
        "rama": "biologica",
        "nivel": 1,
    },
    TipoAtaque.VACUNA_UNIVERSAL: {
        "nombre": "Vacuna Universal",
        "descripcion": "Defensa sanitaria sobre territorio propio. Elimina Gripe Aviar, Coronavirus y Fatiga en la red de territorios propios conectados.",
        "precio": 1000,
        "rama": "biologica",
        "nivel": 2,
    },
    TipoAtaque.FATIGA: {
        "nombre": "Fatiga",
        "descripcion": "Descripcion 3",
        "precio": 1000,
        "rama": "biologica",
        "nivel": 2,
    },
    TipoAtaque.CORONAVIRUS: {
        "nombre": "Coronavirus",
        "descripcion": "Descripcion 4",
        "precio": 2500,
        "rama": "biologica",
        "nivel": 3,
    },

    # Logistica
    TipoAtaque.ACADEMIA_MILITAR: {
        "nombre": "Academia Militar",
        "descripcion": "Descripcion 5",
        "precio": 500,
        "rama": "logistica",
        "nivel": 1,
    },
    TipoAtaque.INHIBIDOR_SENAL: {
        "nombre": "Inhibidor de Señal",
        "descripcion": "Descripcion 6",
        "precio": 1000,
        "rama": "logistica",
        "nivel": 2,
    },
    TipoAtaque.PROPAGANDA_SUBVERSIVA: {
        "nombre": "Propaganda Subversiva",
        "descripcion": "Descripcion 7",
        "precio": 1000,
        "rama": "logistica",
        "nivel": 2,
    },
    TipoAtaque.MURO_FRONTERIZO: {
        "nombre": "Muro Fronterizo",
        "descripcion": "Descripcion 8",
        "precio": 1500,
        "rama": "logistica",
        "nivel": 3,
    },
    TipoAtaque.SANCIONES_INTERNACIONALES: {
        "nombre": "Sanciones Internacionales",
        "descripcion": "Descripcion 9",
        "precio": 2500,
        "rama": "logistica",
        "nivel": 3,
    },

    # Artillería
    TipoAtaque.MORTERO_TACTICO: {
        "nombre": "Mortero Táctico",
        "descripcion": "Descripcion 10",
        "precio": 500,
        "rama": "artilleria",
        "nivel": 1,
    },
    TipoAtaque.MISIL_CRUCERO: {
        "nombre": "Misil Crucero",
        "descripcion": "Descripcion 11",
        "precio": 1500,
        "rama": "artilleria",
        "nivel": 2,
    },
    TipoAtaque.CABEZA_NUCLEAR: {
        "nombre": "Cabeza Nuclear",
        "descripcion": "Descripcion 12",
        "precio": 3000,
        "rama": "artilleria",
        "nivel": 3,
    },
    TipoAtaque.BOMBA_RACIMO: {
        "nombre": "Bomba de Racimo",
        "descripcion": "Descripcion 13",
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