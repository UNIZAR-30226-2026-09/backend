from app.core.logica_juego.config_ataques_especiales import TipoAtaque

ARBOL_TECNOLOGICO = {
    "biologica": {
        1: [TipoAtaque.GRIPE_AVIAR],
        2: [TipoAtaque.VACUNA_UNIVERSAL, TipoAtaque.FATIGA],
        3: [TipoAtaque.CORONAVIRUS]
    },
    "logistica": {
        1: [TipoAtaque.ACADEMIA_MILITAR],
        2: [TipoAtaque.INHIBIDOR_SENAL, TipoAtaque.PROPAGANDA_SUBVERSIVA],
        3: [TipoAtaque.MURO_FRONTERIZO, TipoAtaque.SANCIONES_INTERNACIONALES]
    },
    "artilleria": {
        1: [TipoAtaque.MORTERO_TACTICO],
        2: [TipoAtaque.MISIL_CRUCERO],
        3: [TipoAtaque.CABEZA_NUCLEAR, TipoAtaque.BOMBA_RACIMO]
    }
}

PRECIOS_TECNOLOGIA = {
    # Guerra Biológica
    TipoAtaque.GRIPE_AVIAR: 500,
    TipoAtaque.VACUNA_UNIVERSAL: 1000,
    TipoAtaque.FATIGA: 1000,
    TipoAtaque.CORONAVIRUS: 2500,
    
    # Logística y Operaciones
    TipoAtaque.ACADEMIA_MILITAR: 500,
    TipoAtaque.INHIBIDOR_SENAL: 1000,
    TipoAtaque.PROPAGANDA_SUBVERSIVA: 1000,
    TipoAtaque.MURO_FRONTERIZO: 1500, 
    TipoAtaque.SANCIONES_INTERNACIONALES: 2500,
    
    # Artillería
    TipoAtaque.MORTERO_TACTICO: 500,
    TipoAtaque.MISIL_CRUCERO: 1500,
    TipoAtaque.CABEZA_NUCLEAR: 3000,
    TipoAtaque.BOMBA_RACIMO: 2000
}