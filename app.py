from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS
from db import get_connection
app = Flask(__name__)
CORS(app)


TURNSTILE_SECRET_KEY = "0x4AAAAAABHphN1BKsuKf4HkLVE9jRuJdyc"

# Configuración del servidor de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'uxlabti@unca.edu.mx'  # Tu cuenta real
app.config['MAIL_PASSWORD'] = 'uram xkfx ejsi gqqf'        # Usa variable de entorno para producción
app.config['MAIL_DEFAULT_SENDER'] = 'uxlabti@unca.edu.mx'  # Misma cuenta o dominio permitido

mail = Mail(app)
@app.route('/solicitudes', methods=['POST'])
def submit_form():
    try:
        data = request.get_json()

        # Datos del usuario
        first_name = data.get('nombre')
        last_name = data.get('apellido')
        email = data.get('email')
        interest = data.get('areaInteres')
        message = data.get('mensaje')

        # === Correo para el usuario (agradecimiento) ===
        user_subject = "Gracias por tu solicitud"
        user_body = f"""
Hola {first_name} {last_name},

Gracias por contactarnos. Recibimos tu mensaje con el siguiente contenido:

Área de interés: {interest}
Mensaje: {message}

Te responderemos pronto.

Saludos,
El equipo del LAB-UX
        """
        user_msg = Message(subject=user_subject, recipients=[email], body=user_body)
        mail.send(user_msg)

        # === Correo para el LAB-UX (notificación interna) ===
        admin_subject = "Nueva solicitud recibida"
        admin_body = f"""
Se ha recibido una nueva solicitud de contacto.

Nombre: {first_name} {last_name}
Correo: {email}
Área de interés: {interest}
Mensaje: {message}
        """
        admin_msg = Message(subject=admin_subject, recipients=['uxlabti@unca.edu.mx'], body=admin_body)
        mail.send(admin_msg)

        return jsonify({"message": "Formulario recibido y correos enviados exitosamente"}), 200

    except Exception as e:
        print({"error": str(e)})
        return jsonify({"error": str(e)}), 400






@app.route('/usuarios', methods=['POST'])
def create_usuario():
    data = request.get_json() or {}
    nombre   = data.get('nombre')
    correo   = data.get('correo')
    password = data.get('password')

    if not all([nombre, correo, password]):
        return jsonify({'success': False, 'error': 'Faltan nombre, correo o password'}), 400

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "INSERT INTO Usuario (nombre, correo, password) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nombre, correo, password))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return jsonify({
            'success': True,
            'usuario': {'id': nuevo_id, 'nombre': nombre, 'correo': correo}
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    # Ejemplo de filtros opcionales: ?nombre=ana&correo=xyz
    filtros = []
    params  = []

    if 'nombre' in request.args:
        filtros.append("nombre LIKE %s")
        params.append(f"%{request.args['nombre']}%")
    if 'correo' in request.args:
        filtros.append("correo = %s")
        params.append(request.args['correo'])

    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    sql   = f"SELECT * FROM Usuario {where}"

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        filas = cursor.fetchall()
        return jsonify({
            'success': True,
            'usuarios': filas,
            'total': len(filas)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'usuarios': [], 'total': 0, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/usuarios/<int:id>', methods=['GET'])
def get_usuario_por_id(id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Usuario WHERE id = %s", (id,))
        fila = cursor.fetchone()
        if not fila:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        return jsonify({'success': True, 'usuario': fila}), 200
    finally:
        cursor.close()
        conn.close()


@app.route('/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    data = request.get_json() or {}
    campos = []
    params = []

    for campo in ('nombre', 'correo', 'password'):
        if campo in data:
            campos.append(f"{campo} = %s")
            params.append(data[campo])

    if not campos:
        return jsonify({'success': False, 'error': 'No hay campos para actualizar'}), 400

    params.append(id)
    sql = f"UPDATE Usuario SET {', '.join(campos)} WHERE id = %s"

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/usuarios/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM Usuario WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/usuarios/login', methods=['POST'])
def login_usuario():
    data = request.get_json() or {}
    print("🔍 Datos recibidos:", data)
    correo   = data.get('email')
    password = data.get('password')

    if not all([correo, password]):
        return jsonify({'success': False, 'error': 'Faltan correo o password'}), 400

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM Usuario WHERE email = %s",
            (correo,)
        )
        user = cursor.fetchone()
        if not user or user['password'] != password:
            return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401

        # opcional: eliminar password antes de devolverlo
        del user['password']
        return jsonify({'success': True, 'usuario': user}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
