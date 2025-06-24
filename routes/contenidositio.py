from flask import Blueprint, request, jsonify
from db import get_connection
import os
import uuid
from werkzeug.utils import secure_filename

bp_contenido = Blueprint('contenido', __name__)

UPLOAD_FOLDER = 'src/uploads/contenido'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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

def delete_imagen(filename):
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

@bp_contenido.route('/contenido', methods=['GET'])
def listar_contenido():
    conn = None
    cursor = None
    try:
        filtros = []
        valores = []
        # Lista de campos que puedes filtrar
        campos_filtrables = ['tipo', 'titulo', 'texto', 'estado', 'orden', 'fecha_creacion', 'fecha_actualizacion']

        for campo in campos_filtrables:
            valor = request.args.get(campo)
            if valor is not None:
                filtros.append(f"{campo} = %s")
                valores.append(valor)

        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"SELECT * FROM Contenido_Sitio {where} ORDER BY orden ASC"

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, valores)
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_contenido.route('/contenido/<int:id>', methods=['GET'])
def obtener_contenido(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Contenido_Sitio WHERE ID = %s", (id,))
        item = cursor.fetchone()
        if item:
            return jsonify(item)
        return jsonify({'error': 'Contenido no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_contenido.route('/contenido', methods=['POST'])
def crear_contenido():
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

        tipo = data.get('tipo')
        titulo = data.get('titulo')
        texto = data.get('texto')
        link_redireccion = data.get('link_redireccion')
        estado = data.get('estado', 'activo')
        orden = data.get('orden', 1)
        fecha_creacion = data.get('fecha_creacion')
        fecha_actualizacion = data.get('fecha_actualizacion')

        if not all([tipo, titulo, texto, estado, orden, fecha_creacion, fecha_actualizacion]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        conn = get_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO Contenido_Sitio
            (tipo, titulo, texto, imagen, link_redireccion, estado, orden, fecha_creacion, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            tipo, titulo, texto, imagen, link_redireccion, estado, orden, fecha_creacion, fecha_actualizacion
        ))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_contenido.route('/contenido/<int:id>', methods=['PUT'])
def actualizar_contenido(id):
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

        for campo in ['tipo', 'titulo', 'texto', 'link_redireccion', 'estado', 'orden', 'fecha_creacion', 'fecha_actualizacion']:
            if campo in data:
                campos.append(f"{campo} = %s")
                params.append(data[campo])

        if nueva_imagen:
            # Eliminar imagen anterior
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT imagen FROM Contenido_Sitio WHERE ID = %s", (id,))
            anterior = cursor.fetchone()
            if anterior and anterior['imagen']:
                delete_imagen(anterior['imagen'])
            campos.append("imagen = %s")
            params.append(nueva_imagen)
            cursor.close()
            conn.close()

        if campos:
            params.append(id)
            sql = f"UPDATE Contenido_Sitio SET {', '.join(campos)} WHERE ID = %s"
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
        return jsonify({'mensaje': 'Contenido actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_contenido.route('/contenido/<int:id>', methods=['DELETE'])
def eliminar_contenido(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT imagen FROM Contenido_Sitio WHERE ID = %s", (id,))
        item = cursor.fetchone()
        if item and item['imagen']:
            delete_imagen(item['imagen'])
        cursor.execute("DELETE FROM Contenido_Sitio WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Contenido eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()