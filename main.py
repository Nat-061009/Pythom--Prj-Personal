"""API REST para una tienda de peluches Chikawa con FastAPI y SQLite."""
from contextlib import asynccontextmanager
import sqlite3
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import get_connection, initialize_database


class Persona(BaseModel):
    cedula: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=100)
    telefono: str = Field(min_length=1, max_length=30)
    correo: str = Field(min_length=3, max_length=120)


class Cliente(BaseModel):
    cedula: str = Field(min_length=1, max_length=30)
    fecha_registro: date


class Tienda(BaseModel):
    identificador: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=80)
    direccion: str = Field(min_length=1, max_length=160)
    telefono: str = Field(min_length=1, max_length=30)


class Trabajador(BaseModel):
    cedula: str = Field(min_length=1, max_length=30)
    puesto: str = Field(min_length=1, max_length=80)
    salario: float = Field(ge=0)
    tienda_id: str = Field(min_length=1, max_length=30)


class Peluche(BaseModel):
    identificador: str = Field(min_length=1, max_length=30)
    descripcion: str = Field(min_length=1, max_length=160)
    precio: float = Field(ge=0)
    tamano: str = Field(min_length=1, max_length=40)
    coleccion: str = Field(min_length=1, max_length=80)
    imagen: str = ""


class Factura(BaseModel):
    identificador: str = Field(min_length=1, max_length=30)
    fecha: date
    cliente_cedula: str = Field(min_length=1, max_length=30)
    trabajador_cedula: str = Field(min_length=1, max_length=30)
    tienda_id: str = Field(min_length=1, max_length=30)
    peluche_id: str = Field(min_length=1, max_length=30)
    cantidad: int = Field(gt=0)
    total: float = Field(ge=0)


MODELS = {
    "persona": Persona,
    "cliente": Cliente,
    "tienda": Tienda,
    "trabajador": Trabajador,
    "peluche": Peluche,
    "factura": Factura,
}
PRIMARY_KEYS = {
    "persona": "cedula",
    "cliente": "cedula",
    "tienda": "identificador",
    "trabajador": "cedula",
    "peluche": "identificador",
    "factura": "identificador",
}
TABLES = set(MODELS)


def quoted_columns(data: dict):
    return list(data), list(data.values())


def db_error(exc: sqlite3.IntegrityError):
    raise HTTPException(
        409,
        "No se puede completar la operacion: clave duplicada o relacion inexistente/en uso.",
    ) from exc


def serialize(row):
    return dict(row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Tienda de peluches Chikawa", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/{table}")
def list_rows(table: str):
    if table not in TABLES:
        raise HTTPException(404, "Entidad no encontrada")
    with get_connection() as conn:
        return [serialize(row) for row in conn.execute(f"SELECT * FROM {table}")]


@app.get("/api/{table}/{key}")
def get_row(table: str, key: str):
    if table not in TABLES:
        raise HTTPException(404, "Entidad no encontrada")
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE {PRIMARY_KEYS[table]} = ?",
            (key,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    return serialize(row)


@app.post("/api/{table}", status_code=201)
def create_row(table: str, payload: dict):
    if table not in TABLES:
        raise HTTPException(404, "Entidad no encontrada")
    data = MODELS[table].model_validate(payload).model_dump(mode="json")
    columns, values = quoted_columns(data)
    try:
        with get_connection() as conn:
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
    except sqlite3.IntegrityError as exc:
        db_error(exc)
    return data


@app.put("/api/{table}/{key}")
def update_row(table: str, key: str, payload: dict):
    if table not in TABLES:
        raise HTTPException(404, "Entidad no encontrada")
    data = MODELS[table].model_validate(payload).model_dump(mode="json")
    pk = PRIMARY_KEYS[table]
    if data[pk] != key:
        raise HTTPException(400, "La clave de la URL debe coincidir con el cuerpo")
    try:
        with get_connection() as conn:
            result = conn.execute(
                f"UPDATE {table} SET {', '.join(f'{column} = ?' for column in data if column != pk)} WHERE {pk} = ?",
                [value for column, value in data.items() if column != pk] + [key],
            )
    except sqlite3.IntegrityError as exc:
        db_error(exc)
    if result.rowcount == 0:
        raise HTTPException(404, "Registro no encontrado")
    return data


@app.delete("/api/{table}/{key}", status_code=204)
def delete_row(table: str, key: str):
    if table not in TABLES:
        raise HTTPException(404, "Entidad no encontrada")
    try:
        with get_connection() as conn:
            result = conn.execute(
                f"DELETE FROM {table} WHERE {PRIMARY_KEYS[table]} = ?",
                (key,),
            )
    except sqlite3.IntegrityError as exc:
        db_error(exc)
    if result.rowcount == 0:
        raise HTTPException(404, "Registro no encontrado")


@app.get("/api/factura/{identificador}/detalle")
def invoice_detail(identificador: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT f.*, p.descripcion AS peluche, c.cedula AS cliente
            FROM factura f
            JOIN peluche p ON p.identificador = f.peluche_id
            JOIN cliente c ON c.cedula = f.cliente_cedula
            WHERE f.identificador = ?
            """,
            (identificador,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Factura no encontrada")
    return serialize(row)
