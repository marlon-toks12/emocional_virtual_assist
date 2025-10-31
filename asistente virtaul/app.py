# ---------------------------------------------
# app.py — Flask con Inicio, Registro y Login
# ---------------------------------------------
# Ahora el home muestra los datos completos del usuario logueado
# ---------------------------------------------

import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, session

app = Flask(__name__)
app.secret_key = "superclave"  # Necesario para usar sesiones
DATABASE = "usuarios.db"


# ---------------------------------------------
# CONEXIÓN A LA BASE DE DATOS
# ---------------------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# ---------------------------------------------
# CREACIÓN / INICIALIZACIÓN DE LA BASE DE DATOS
# ---------------------------------------------
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        #tabla de usuarios
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        telefono TEXT,
                        direccion TEXT,
                        correo TEXT UNIQUE,
                        usuario TEXT UNIQUE,
                        clave TEXT
                    )''')

        #tabla de mensajes del asistente
        c.execute('''CREATE TABLE IF NOT EXISTS mensajes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER,
                        mensaje_usuario TEXT,
                        respuesta_asistente TEXT,
                        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                    )''')

        # Crear usuario admin si no existe
        c.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        if not c.fetchone():
            c.execute("""INSERT INTO usuarios 
                         (nombre, telefono, direccion, correo, usuario, clave)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      ("Administrador", "0000000000", "Sin dirección", "admin@correo.com", "admin", "1234"))
        conn.commit()



# ---------------------------------------------
# RUTA PRINCIPAL
# ---------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------
# LOGIN
# ---------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND clave = ?", (usuario, clave))
        user = cursor.fetchone()

        if user:
            # Guardamos los datos en sesión para usarlos en home
            session["usuario_id"] = user["id"]
            session["usuario_nombre"] = user["nombre"]
            return redirect(url_for("home"))
        else:
            error = "Usuario o contraseña incorrectos"

    return render_template("login.html", error=error)


# ---------------------------------------------
# REGISTRO
# ---------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    mensaje = None

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        direccion = request.form["direccion"]
        correo = request.form["correo"]
        usuario = request.form["usuario"]
        clave = request.form["clave"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE usuario = ? OR correo = ?", (usuario, correo))
        existente = cursor.fetchone()

        if existente:
            error = "El usuario o correo ya están registrados. Intenta con otros datos."
        else:
            cursor.execute("""
                INSERT INTO usuarios (nombre, telefono, direccion, correo, usuario, clave)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, telefono, direccion, correo, usuario, clave))
            conn.commit()
            mensaje = "Registro exitoso. Ahora puedes iniciar sesión."
            return redirect(url_for("login"))

    return render_template("register.html", error=error, mensaje=mensaje)


# ---------------------------------------------
# HOME — Página personal del usuario
# ---------------------------------------------
@app.route("/home")
def home():
    # Verificamos si el usuario está logueado
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],))
    user = cursor.fetchone()

    return render_template("home.html", user=user)

# ---------------------------------------------
# ASISTENTE VIRTUAL EMOCIONAL
# ---------------------------------------------
@app.route("/asistente", methods=["GET", "POST"])
def asistente():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        mensaje_usuario = request.form["mensaje"]

        # Lógica simple de respuesta emocional
        if any(palabra in mensaje_usuario.lower() for palabra in ["triste", "mal", "deprimido"]):
            respuesta = "Lamento que te sientas así 😔, recuerda que todo mejora con el tiempo. Estoy aquí para escucharte."
        elif any(palabra in mensaje_usuario.lower() for palabra in ["feliz", "contento", "alegre"]):
            respuesta = "¡Qué bueno escuchar eso! 😄 Mantén esa energía positiva."
        else:
            respuesta = "Entiendo lo que dices 😊. Cuéntame más sobre cómo te sientes."

        # Guardar mensaje y respuesta en la base de datos
        cursor.execute("""
            INSERT INTO mensajes (usuario_id, mensaje_usuario, respuesta_asistente)
            VALUES (?, ?, ?)
        """, (session["usuario_id"], mensaje_usuario, respuesta))
        conn.commit()

    # Recuperar historial del usuario logueado
    cursor.execute("""
        SELECT mensaje_usuario, respuesta_asistente, fecha
        FROM mensajes WHERE usuario_id = ?
        ORDER BY fecha ASC
    """, (session["usuario_id"],))
    historial = cursor.fetchall()

    return render_template("asistente.html", historial=historial)


# ---------------------------------------------
# LOGOUT
# ---------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
