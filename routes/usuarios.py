from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from db import get_connection

bp = Blueprint('usuarios', __name__)

@bp.route('/solicitudes', methods=['POST'])
def submit_form():
    try:
        data = request.get_json()
        first_name = data.get('nombre')
        last_name = data.get('apellido')
        email = data.get('email')
        interest = data.get('areaInteres')
        message = data.get('mensaje')

        # Correo para el usuario
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
        current_app.extensions['mail'].send(user_msg)

        # Correo para el LAB-UX
        admin_subject = "Nueva solicitud recibida"
        admin_body = f"""
Se ha recibido una nueva solicitud de contacto.

Nombre: {first_name} {last_name}
Correo: {email}
Área de interés: {interest}
Mensaje: {message}
        """
        admin_msg = Message(subject=admin_subject, recipients=['uxlabti@unca.edu.mx'], body=admin_body)
        current_app.extensions['mail'].send(admin_msg)

        return jsonify({"message": "Formulario recibido y correos enviados exitosamente"}), 200

    except Exception as e:
        print({"error": str(e)})
        return jsonify({"error": str(e)}), 400

@bp.route('/usuarios', methods=['POST'])
def create_usuario():
    data = request.get_json() or {}
    nombre   = data.get('nombre')
    correo   = data.get('correo')
    password = data.get('password')
    tipo_usuario = data.get('tipo_usuario', 'usuario')

    if not all([nombre, correo, password]):
        return jsonify({'success': False, 'error': 'Faltan nombre, correo o password'}), 400

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "INSERT INTO Usuario (nombre, correo, password, tipo_usuario) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, correo, password, tipo_usuario))
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

@bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    filtros = []
    params  = []

    # Búsqueda general en varios campos
    q = request.args.get('q')
    campos_busqueda = ['nombre', 'correo', 'username', 'apellido', 'telefono', 'tipo_usuario', 'estado']
    if q:
        condiciones = [f"{campo} LIKE %s" for campo in campos_busqueda]
        filtros.append("(" + " OR ".join(condiciones) + ")")
        params.extend([f"%{q}%"] * len(campos_busqueda))

    # Filtros específicos
    if 'nombre' in request.args:
        filtros.append("nombre LIKE %s")
        params.append(f"%{request.args['nombre']}%")
    if 'correo' in request.args:
        filtros.append("correo = %s")
        params.append(request.args['correo'])
    if 'tipo_usuario' in request.args:
        filtros.append("tipo_usuario = %s")
        params.append(request.args['tipo_usuario'])
    if 'estado' in request.args:
        filtros.append("estado = %s")
        params.append(request.args['estado'])
    if 'username' in request.args:
        filtros.append("username = %s")
        params.append(request.args['username'])

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

@bp.route('/usuarios/<int:id>', methods=['GET'])
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

@bp.route('/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    data = request.get_json() or {}
    campos = []
    params = []

    for campo in ('nombre', 'apellido', 'correo', 'password', 'telefono', 'tipo_usuario', 'estado'):
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

@bp.route('/usuarios/<int:id>', methods=['DELETE'])
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

@bp.route('/usuarios/login', methods=['POST'])
def login_usuario():
    data = request.get_json() or {}
    correo   = data.get('email')
    password = data.get('password')

    if not all([correo, password]):
        return jsonify({'success': False, 'error': 'Faltan correo o password'}), 400

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM Usuario WHERE correo = %s",
            (correo,)
        )
        user = cursor.fetchone()
        if not user or user['password'] != password:
            return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401

        del user['password']
        return jsonify({'success': True, 'usuario': user}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/usuarios/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    correo = data.get('email')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM Usuario WHERE correo = %s",
            (correo,)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no válido'}), 401

        name = user['nombre']
        email = user['correo']
        password = user['password']

        user_subject = "Recuperación de tu contraseña"
        user_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 0; margin: 0;">
            <div style="background-color: #000000; color: #ffffff; padding: 15px 20px; text-align: center; font-size: 1.5em;">
            LAB-UX
            </div>
            <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
            <h2 style="color: #4CAF50;">Recuperación de tu contraseña</h2>
            <p>Hola <strong>{name}</strong>,</p>
            <p>Recibimos una solicitud para recuperar tu contraseña. Aquí tienes tu contraseña actual:</p>
            <div style="background-color: #f1f1f1; padding: 10px; font-size: 1.2em; margin: 20px 0; border-radius: 5px;">
                <strong>Contraseña:</strong> {password}
            </div>
            <p style="color: #555;">Si no has solicitado este cambio, por favor ignora este correo.</p>
            <p>Si tienes algún problema o deseas cambiar tu contraseña, no dudes en ponerte en contacto con nosotros.</p>
            <br>
            <p>Saludos,<br>El equipo del LAB-UX</p>
            </div>
        </body>
        </html>
        """
        user_msg = Message(subject=user_subject, recipients=[email], html=user_body)
        current_app.extensions['mail'].send(user_msg)

        admin_subject = "Solicitud de recuperación de contraseña"
        admin_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #4CAF50;">Nueva solicitud de recuperación de contraseña</h2>
            <p><strong>Nombre:</strong> {name}</p>
            <p><strong>Correo:</strong> {email}</p>
            <p><strong>Contraseña recuperada:</strong> {password}</p>
        </body>
        </html>
        """
        admin_msg = Message(subject=admin_subject, recipients=['uxlabti@unca.edu.mx'], html=admin_body)
        current_app.extensions['mail'].send(admin_msg)

        return jsonify({"message": "Correo con la contraseña enviado exitosamente",'success': True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()