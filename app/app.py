from flask import Flask, render_template, request, redirect, url_for, jsonify
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import os

app = Flask(__name__)

# Variables por entorno (Kubernetes Secret -> envFrom)
DB_HOST = os.environ.get("DB_HOST", "app-db")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "incidencias")
DB_USER = os.environ.get("DB_USER", "inc_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "CambiarEstaPass123!")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,   # para que el HTML pueda usar inc.id, inc.titulo, etc.
        autocommit=True,
        charset="utf8mb4",
    )

def init_db():
    # Misma estructura lógica que en SQLite, adaptada a MariaDB
    sql = """
    CREATE TABLE IF NOT EXISTS incidencias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        prioridad ENUM('baja','media','alta') NOT NULL DEFAULT 'media',
        estado ENUM('abierta','en_progreso','resuelta') NOT NULL DEFAULT 'abierta',
        creado_en DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute(sql)
    finally:
        conn.close()

@app.route("/")
def index():
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM incidencias ORDER BY creado_en DESC")
            incidencias = c.fetchall()
    finally:
        conn.close()

    # Renderiza templates/index.html (el tuyo)
    return render_template("index.html", incidencias=incidencias)

@app.route("/incidencias", methods=["GET"])
def listar_incidencias_json():
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM incidencias ORDER BY creado_en DESC")
            incidencias = c.fetchall()
    finally:
        conn.close()
    return jsonify(incidencias)

@app.route("/incidencias", methods=["POST"])
def crear_incidencia():
    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    prioridad = request.form.get("prioridad", "media")

    if not titulo:
        return "El título es obligatorio", 400

    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO incidencias (titulo, descripcion, prioridad, estado, creado_en) "
                "VALUES (%s, %s, %s, %s, %s)",
                (titulo, descripcion, prioridad, "abierta", datetime.now())
            )
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/incidencias/<int:incidencia_id>/estado", methods=["POST"])
def cambiar_estado(incidencia_id):
    nuevo_estado = request.form.get("estado")
    if nuevo_estado not in ("abierta", "en_progreso", "resuelta"):
        return "Estado no válido", 400

    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute(
                "UPDATE incidencias SET estado = %s WHERE id = %s",
                (nuevo_estado, incidencia_id)
            )
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/incidencias/<int:incidencia_id>/delete", methods=["POST"])
def borrar_incidencia(incidencia_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM incidencias WHERE id = %s", (incidencia_id,))
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # Crea tabla si no existe (idempotente)
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)