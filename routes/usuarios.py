import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_mail import Message
from db import get_connection
from werkzeug.utils import secure_filename

bp = Blueprint('usuarios', __name__)

UPLOAD_FOLDER = 'src/uploads/usuarios'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_foto(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(file_path)
        return unique_name  # Solo el nombre único del archivo
    return None

def delete_foto(filename):
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

@bp.route('/usuarios/<filename>')
def get_foto_usuario(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

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
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            foto = None
            if 'foto' in request.files:
                foto = save_foto(request.files['foto'])
        else:
            data = request.get_json() or {}
            foto = data.get('foto')

        nombre        = data.get('nombre')
        apellido      = data.get('apellido')
        correo        = data.get('correo')
        password      = data.get('password')
        telefono      = data.get('telefono')
        tipo_usuario  = data.get('tipo_usuario', 'usuario')
        estado        = data.get('estado', 'activo')
        username      = data.get('username')

        if not all([nombre, correo, password]):
            return jsonify({'success': False, 'error': 'Faltan nombre, correo o password'}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            INSERT INTO Usuario
            (nombre, apellido, correo, password, telefono, tipo_usuario, estado, username, foto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            nombre, apellido, correo, password, telefono, tipo_usuario, estado, username, foto
        ))
        usuario_id = cursor.lastrowid

        # 2. Usuario_Detalle (opcional)
        detalle = data.get('detalle')
        if detalle:
            sql = """INSERT INTO Usuario_Detalle (ID_usuario, telefono, direccion) VALUES (%s, %s, %s)"""
            cursor.execute(sql, (usuario_id, detalle.get('telefono'), detalle.get('direccion')))

        # 3. Usuario_Area_Investigacion (lista de IDs de áreas)
        areas = data.get('areas_investigacion', [])
        for area in areas:
            sql = "INSERT INTO Usuario_Area_Investigacion (ID_usuario, ID_area) VALUES (%s, %s)"
            cursor.execute(sql, (usuario_id, area.get('ID_area')))

        # 4. Experiencia_Laboral (lista de experiencias)
        experiencias = data.get('experiencia_laboral', [])
        for exp in experiencias:
            sql = """INSERT INTO Experiencia_Laboral (ID_usuario, empresa, puesto, fecha_inicio, fecha_fin, descripcion)
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                usuario_id, exp.get('empresa'), exp.get('puesto'),
                exp.get('fecha_inicio'), exp.get('fecha_fin'), exp.get('descripcion')
            ))

        # 5. Formacion_Academica (lista de formaciones)
        formaciones = data.get('formacion_academica', [])
        for form in formaciones:
            sql = """INSERT INTO Formacion_Academica (ID_usuario, institucion, grado, fecha_inicio, fecha_fin, descripcion)
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                usuario_id, form.get('institucion'), form.get('grado'),
                form.get('fecha_inicio'), form.get('fecha_fin'), form.get('descripcion')
            ))

        conn.commit()
        return jsonify({'success': True, 'usuario_id': usuario_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    filtros = []
    params  = []
    q = request.args.get('q')
    campos_busqueda = ['nombre', 'correo', 'username', 'apellido', 'telefono', 'tipo_usuario', 'estado']
    if q:
        condiciones = [f"{campo} LIKE %s" for campo in campos_busqueda]
        filtros.append("(" + " OR ".join(condiciones) + ")")
        params.extend([f"%{q}%"] * len(campos_busqueda))
    for campo in ['nombre', 'correo', 'tipo_usuario', 'estado', 'username']:
        if campo in request.args:
            filtros.append(f"{campo} = %s")
            params.append(request.args[campo])
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    sql   = f"SELECT * FROM Usuario {where}"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        usuarios = cursor.fetchall()
        for usuario in usuarios:
            uid = usuario['ID']
            # Si hay foto, agrega la URL pública
            if usuario.get('foto'):
                usuario['foto_url'] = f"/usuarios/{usuario['foto']}"
            # Usuario_Detalle
            cursor.execute("SELECT * FROM Usuario_Detalle WHERE ID_usuario = %s", (uid,))
            usuario['detalle'] = cursor.fetchone()
            # Usuario_Area_Investigacion
            cursor.execute("""
                SELECT uai.*, ai.nombre AS area_nombre, ai.descripcion AS area_descripcion
                FROM Usuario_Area_Investigacion uai
                LEFT JOIN Area_Investigacion ai ON uai.ID_area = ai.ID
                WHERE uai.ID_usuario = %s
            """, (uid,))
            usuario['areas_investigacion'] = cursor.fetchall()
            # Experiencia_Laboral
            cursor.execute("SELECT * FROM Experiencia_Laboral WHERE ID_usuario = %s", (uid,))
            usuario['experiencia_laboral'] = cursor.fetchall()
            # Formacion_Academica
            cursor.execute("SELECT * FROM Formacion_Academica WHERE ID_usuario = %s", (uid,))
            usuario['formacion_academica'] = cursor.fetchall()
        return jsonify({'success': True, 'usuarios': usuarios, 'total': len(usuarios)}), 200
    except Exception as e:
        return jsonify({'success': False, 'usuarios': [], 'total': 0, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/usuarios/<int:id>', methods=['GET'])
def get_usuario_por_id(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Usuario WHERE id = %s", (id,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        uid = usuario['ID']
        # Si hay foto, agrega la URL pública
        if usuario.get('foto'):
            usuario['foto_url'] = f"/usuarios/{usuario['foto']}"
        # Usuario_Detalle
        cursor.execute("SELECT * FROM Usuario_Detalle WHERE ID_usuario = %s", (uid,))
        usuario['detalle'] = cursor.fetchone()
        # Usuario_Area_Investigacion
        cursor.execute("""
            SELECT uai.*, ai.nombre AS area_nombre, ai.descripcion AS area_descripcion
            FROM Usuario_Area_Investigacion uai
            LEFT JOIN Area_Investigacion ai ON uai.ID_area = ai.ID
            WHERE uai.ID_usuario = %s
        """, (uid,))
        usuario['areas_investigacion'] = cursor.fetchall()
        # Experiencia_Laboral
        cursor.execute("SELECT * FROM Experiencia_Laboral WHERE ID_usuario = %s", (uid,))
        usuario['experiencia_laboral'] = cursor.fetchall()
        # Formacion_Academica
        cursor.execute("SELECT * FROM Formacion_Academica WHERE ID_usuario = %s", (uid,))
        usuario['formacion_academica'] = cursor.fetchall()

        return jsonify({'success': True, 'usuario': usuario}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            nueva_foto = None
            if 'foto' in request.files:
                nueva_foto = save_foto(request.files['foto'])
        else:
            data = request.get_json() or {}
            nueva_foto = data.get('foto')

        campos = []
        params = []

        for campo in ('nombre', 'apellido', 'correo', 'password', 'telefono', 'tipo_usuario', 'estado'):
            if campo in data:
                campos.append(f"{campo} = %s")
                params.append(data[campo])

        # Si hay nueva foto, obtener la anterior y actualizar
        if nueva_foto:
            # Obtener foto anterior
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT foto FROM Usuario WHERE ID = %s", (id,))
            anterior = cursor.fetchone()
            if anterior and anterior['foto']:
                delete_foto(anterior['foto'])
            campos.append("foto = %s")
            params.append(nueva_foto)
            cursor.close()
            conn.close()

        if campos:
            params.append(id)
            sql = f"UPDATE Usuario SET {', '.join(campos)} WHERE ID = %s"
        else:
            sql = None

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if sql:
            cursor.execute(sql, params)

        # 2. Actualizar o insertar Usuario_Detalle
        detalle = data.get('detalle')
        if detalle:
            cursor.execute("SELECT * FROM Usuario_Detalle WHERE ID_usuario = %s", (id,))
            if cursor.fetchone():
                # Actualizar
                detalle_campos = []
                detalle_params = []
                for campo in ('telefono', 'direccion'):  # agrega más campos según tu modelo
                    if campo in detalle:
                        detalle_campos.append(f"{campo} = %s")
                        detalle_params.append(detalle[campo])
                if detalle_campos:
                    detalle_params.append(id)
                    cursor.execute(f"UPDATE Usuario_Detalle SET {', '.join(detalle_campos)} WHERE ID_usuario = %s", detalle_params)
            else:
                # Insertar
                cursor.execute(
                    "INSERT INTO Usuario_Detalle (ID_usuario, telefono, direccion) VALUES (%s, %s, %s)",
                    (id, detalle.get('telefono'), detalle.get('direccion'))
                )

        # 3. Actualizar áreas de investigación (borrar e insertar)
        if 'areas_investigacion' in data:
            cursor.execute("DELETE FROM Usuario_Area_Investigacion WHERE ID_usuario = %s", (id,))
            for area in data['areas_investigacion']:
                cursor.execute("INSERT INTO Usuario_Area_Investigacion (ID_usuario, ID_area) VALUES (%s, %s)", (id, area.get('ID_area')))

        # 4. Actualizar experiencia laboral (borrar e insertar)
        if 'experiencia_laboral' in data:
            cursor.execute("DELETE FROM Experiencia_Laboral WHERE ID_usuario = %s", (id,))
            for exp in data['experiencia_laboral']:
                cursor.execute(
                    """INSERT INTO Experiencia_Laboral (ID_usuario, empresa, puesto, fecha_inicio, fecha_fin, descripcion)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (id, exp.get('empresa'), exp.get('puesto'), exp.get('fecha_inicio'), exp.get('fecha_fin'), exp.get('descripcion'))
                )

        # 5. Actualizar formación académica (borrar e insertar)
        if 'formacion_academica' in data:
            cursor.execute("DELETE FROM Formacion_Academica WHERE ID_usuario = %s", (id,))
            for form in data['formacion_academica']:
                cursor.execute(
                    """INSERT INTO Formacion_Academica (ID_usuario, institucion, grado, fecha_inicio, fecha_fin, descripcion)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (id, form.get('institucion'), form.get('grado'), form.get('fecha_inicio'), form.get('fecha_fin'), form.get('descripcion'))
                )

        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/usuarios/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Obtener foto antes de borrar usuario
        cursor.execute("SELECT foto FROM Usuario WHERE ID = %s", (id,))
        usuario = cursor.fetchone()
        if usuario and usuario['foto']:
            delete_foto(usuario['foto'])
        cursor.execute("DELETE FROM Usuario WHERE ID = %s", (id,))
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