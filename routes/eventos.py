from flask import Blueprint, request, jsonify
from db import get_connection
import os
import uuid
from werkzeug.utils import secure_filename

bp_eventos = Blueprint('eventos', __name__)

UPLOAD_FOLDER = 'src/uploads/eventos'
MATERIAL_FOLDER = 'src/uploads/materiales_evento'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_imagen(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(file_path)
        return unique_name
    return None

def save_material(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(MATERIAL_FOLDER, exist_ok=True)
        file_path = os.path.join(MATERIAL_FOLDER, unique_name)
        file.save(file_path)
        return unique_name
    return None

def delete_file(folder, filename):
    if filename:
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

# --- CRUD Evento_Noticia ---

@bp_eventos.route('/eventos', methods=['GET'])
def listar_eventos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Evento_Noticia ORDER BY fecha DESC")
        eventos = cursor.fetchall()
        for evento in eventos:
            eid = evento['ID']
            # Asistentes externos
            cursor.execute("SELECT * FROM Evento_Asistente WHERE ID_evento = %s", (eid,))
            evento['asistentes'] = cursor.fetchall()
            # Áreas de investigación
            cursor.execute("""
                SELECT eai.ID_area, ai.nombre AS area_nombre
                FROM Evento_Area_Investigacion eai
                LEFT JOIN Area_Investigacion ai ON eai.ID_area = ai.ID
                WHERE eai.ID_evento = %s
            """, (eid,))
            evento['areas_investigacion'] = cursor.fetchall()
            # Materiales
            cursor.execute("SELECT * FROM Material_Evento WHERE ID_evento_noticia = %s", (eid,))
            evento['materiales'] = cursor.fetchall()
        return jsonify(eventos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_eventos.route('/eventos/<int:id>', methods=['GET'])
def obtener_evento(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Evento_Noticia WHERE ID = %s", (id,))
        evento = cursor.fetchone()
        if not evento:
            return jsonify({'error': 'Evento no encontrado'}), 404
        # Asistentes externos
        cursor.execute("SELECT * FROM Evento_Asistente WHERE ID_evento = %s", (id,))
        evento['asistentes'] = cursor.fetchall()
        # Áreas de investigación
        cursor.execute("""
            SELECT eai.ID_area, ai.nombre AS area_nombre
            FROM Evento_Area_Investigacion eai
            LEFT JOIN Area_Investigacion ai ON eai.ID_area = ai.ID
            WHERE eai.ID_evento = %s
        """, (id,))
        evento['areas_investigacion'] = cursor.fetchall()
        # Materiales
        cursor.execute("SELECT * FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
        evento['materiales'] = cursor.fetchall()
        return jsonify(evento)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_eventos.route('/eventos', methods=['POST'])
def crear_evento():
    conn = None
    cursor = None
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = None
            if 'imagen' in request.files:
                imagen = save_imagen(request.files['imagen'])
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen')

        titulo = data.get('titulo')
        descripcion = data.get('descripcion')
        fecha = data.get('fecha')
        lugar = data.get('lugar')
        tipo = data.get('tipo')
        fecha_creacion = data.get('fecha_creacion')
        ID_usuario = data.get('ID_usuario')

        if not all([titulo, descripcion, fecha, lugar, tipo, fecha_creacion, ID_usuario]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        conn = get_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO Evento_Noticia
            (titulo, descripcion, fecha, lugar, tipo, imagen, fecha_creacion, ID_usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            titulo, descripcion, fecha, lugar, tipo, imagen, fecha_creacion, ID_usuario
        ))
        evento_id = cursor.lastrowid

        # Asistentes externos
        asistentes = data.get('asistentes', [])
        for asistente in asistentes:
            cursor.execute(
                "INSERT INTO Evento_Asistente (ID_evento, nombre_externo, email_externo, institucion_externa) VALUES (%s, %s, %s, %s)",
                (evento_id, asistente.get('nombre_externo'), asistente.get('email_externo'), asistente.get('institucion_externa'))
            )
        # Áreas de investigación
        areas = data.get('areas_investigacion', [])
        for area in areas:
            cursor.execute(
                "INSERT INTO Evento_Area_Investigacion (ID_evento, ID_area) VALUES (%s, %s)",
                (evento_id, area.get('ID_area'))
            )
        # Materiales
        materiales = data.get('materiales', [])
        for material in materiales:
            archivo = None
            if request.content_type.startswith('multipart/form-data') and material.get('archivo') in request.files:
                archivo = save_material(request.files[material.get('archivo')])
            else:
                archivo = material.get('archivo')
            cursor.execute(
                "INSERT INTO Material_Evento (ID_evento_noticia, tipo, nombre, archivo) VALUES (%s, %s, %s, %s)",
                (evento_id, material.get('tipo'), material.get('nombre'), archivo)
            )

        conn.commit()
        return jsonify({'id': evento_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_eventos.route('/eventos/<int:id>', methods=['PUT'])
def actualizar_evento(id):
    conn = None
    cursor = None
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            nueva_imagen = None
            if 'imagen' in request.files:
                nueva_imagen = save_imagen(request.files['imagen'])
        else:
            data = request.get_json() or {}
            nueva_imagen = data.get('imagen')

        campos = []
        params = []

        for campo in ['titulo', 'descripcion', 'fecha', 'lugar', 'tipo', 'fecha_creacion', 'ID_usuario']:
            if campo in data:
                campos.append(f"{campo} = %s")
                params.append(data[campo])

        if nueva_imagen:
            # Eliminar imagen anterior
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT imagen FROM Evento_Noticia WHERE ID = %s", (id,))
            anterior = cursor.fetchone()
            if anterior and anterior['imagen']:
                delete_file(UPLOAD_FOLDER, anterior['imagen'])
            campos.append("imagen = %s")
            params.append(nueva_imagen)
            cursor.close()
            conn.close()

        if campos:
            params.append(id)
            sql = f"UPDATE Evento_Noticia SET {', '.join(campos)} WHERE ID = %s"
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)

        # Actualizar asistentes externos
        if 'asistentes' in data:
            cursor.execute("DELETE FROM Evento_Asistente WHERE ID_evento = %s", (id,))
            for asistente in data['asistentes']:
                cursor.execute(
                    "INSERT INTO Evento_Asistente (ID_evento, nombre_externo, email_externo, institucion_externa) VALUES (%s, %s, %s, %s)",
                    (id, asistente.get('nombre_externo'), asistente.get('email_externo'), asistente.get('institucion_externa'))
                )
        # Actualizar áreas de investigación
        if 'areas_investigacion' in data:
            cursor.execute("DELETE FROM Evento_Area_Investigacion WHERE ID_evento = %s", (id,))
            for area in data['areas_investigacion']:
                cursor.execute(
                    "INSERT INTO Evento_Area_Investigacion (ID_evento, ID_area) VALUES (%s, %s)",
                    (id, area.get('ID_area'))
                )
        # Actualizar materiales
        if 'materiales' in data:
            # Eliminar archivos físicos de materiales anteriores
            cursor.execute("SELECT archivo FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
            archivos = cursor.fetchall()
            for arch in archivos:
                if arch['archivo']:
                    delete_file(MATERIAL_FOLDER, arch['archivo'])
            cursor.execute("DELETE FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
            for material in data['materiales']:
                archivo = None
                if request.content_type.startswith('multipart/form-data') and material.get('archivo') in request.files:
                    archivo = save_material(request.files[material.get('archivo')])
                else:
                    archivo = material.get('archivo')
                cursor.execute(
                    "INSERT INTO Material_Evento (ID_evento_noticia, tipo, nombre, archivo) VALUES (%s, %s, %s, %s)",
                    (id, material.get('tipo'), material.get('nombre'), archivo)
                )

        conn.commit()
        return jsonify({'mensaje': 'Evento actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_eventos.route('/eventos/<int:id>', methods=['DELETE'])
def eliminar_evento(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Eliminar imagen física si existe
        cursor.execute("SELECT imagen FROM Evento_Noticia WHERE ID = %s", (id,))
        evento = cursor.fetchone()
        if evento and evento['imagen']:
            delete_file(UPLOAD_FOLDER, evento['imagen'])
        # Eliminar asistentes y áreas relacionadas
        cursor.execute("DELETE FROM Evento_Asistente WHERE ID_evento = %s", (id,))
        cursor.execute("DELETE FROM Evento_Area_Investigacion WHERE ID_evento = %s", (id,))
        # Eliminar materiales y archivos físicos
        cursor.execute("SELECT archivo FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
        archivos = cursor.fetchall()
        for arch in archivos:
            if arch['archivo']:
                delete_file(MATERIAL_FOLDER, arch['archivo'])
        cursor.execute("DELETE FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
        # Eliminar el evento
        cursor.execute("DELETE FROM Evento_Noticia WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Evento eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()