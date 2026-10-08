"""Esquema y utilidades de SQLite para la tienda de peluches Chikawa."""
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tienda_chikawa.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS persona (
  cedula TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  apellido TEXT NOT NULL,
  telefono TEXT NOT NULL,
  correo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cliente (
  cedula TEXT PRIMARY KEY,
  fecha_registro TEXT NOT NULL,
  FOREIGN KEY (cedula) REFERENCES persona(cedula) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS tienda (
  identificador TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  direccion TEXT NOT NULL,
  telefono TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trabajador (
  cedula TEXT PRIMARY KEY,
  puesto TEXT NOT NULL,
  salario REAL NOT NULL CHECK(salario >= 0),
  tienda_id TEXT NOT NULL,
  FOREIGN KEY (cedula) REFERENCES persona(cedula) ON DELETE RESTRICT,
  FOREIGN KEY (tienda_id) REFERENCES tienda(identificador) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS peluche (
  identificador TEXT PRIMARY KEY,
  descripcion TEXT NOT NULL,
  precio REAL NOT NULL CHECK(precio >= 0),
  tamano TEXT NOT NULL,
  coleccion TEXT NOT NULL,
  imagen TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS factura (
  identificador TEXT PRIMARY KEY,
  fecha TEXT NOT NULL,
  cliente_cedula TEXT NOT NULL,
  trabajador_cedula TEXT NOT NULL,
  tienda_id TEXT NOT NULL,
  peluche_id TEXT NOT NULL,
  cantidad INTEGER NOT NULL CHECK(cantidad > 0),
  total REAL NOT NULL CHECK(total >= 0),
  FOREIGN KEY (cliente_cedula) REFERENCES cliente(cedula) ON DELETE RESTRICT,
  FOREIGN KEY (trabajador_cedula) REFERENCES trabajador(cedula) ON DELETE RESTRICT,
  FOREIGN KEY (tienda_id) REFERENCES tienda(identificador) ON DELETE RESTRICT,
  FOREIGN KEY (peluche_id) REFERENCES peluche(identificador) ON DELETE RESTRICT
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(peluche)").fetchall()
        }
        if "imagen" not in columns:
            conn.execute("ALTER TABLE peluche ADD COLUMN imagen TEXT NOT NULL DEFAULT ''")
