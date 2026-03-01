from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
from app.schemas.map import MapDataSchema

router = APIRouter()

# La ruta será GET /api/v1/mapa
@router.get("", response_model=MapDataSchema)
async def obtener_mapa():
    # Buscamos donde esta el json guardado
    json_path = Path("app/core/data/map_aragon.json")
    
    try:
        # Abrimos el archivo y lo cargamos
        with open(json_path, "r", encoding="utf-8") as file:
            mapa_data = json.load(file)
        return mapa_data
    
    except FileNotFoundError:
        # Por si alguien borra o mueve el json sin querer
        raise HTTPException(status_code=404, detail="Archivo del mapa no encontrado")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error al leer el archivo del mapa")