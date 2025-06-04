from flask import Blueprint, request, jsonify
from db import get_connection
import os
from werkzeug.utils import secure_filename

bp = Blueprint('proyecto', __name__)

UPLOAD_FOLDER = 'src/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        return file_path
    return None

@bp.route('/proyectos', methods=['GET'])
def listar_proyectos():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM proyecto")
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/proyectos/<int:id>', methods=['GET'])
def obtener_proyecto(id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM proyecto WHERE id = %s", (id,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        if resultado:
            return jsonify(resultado)
        return jsonify({'error': 'Proyecto no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/proyectos', methods=['POST'])
def crear_proyecto():
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen_path = None
            if 'imagen' in request.files:
                imagen_path = save_image(request.files['imagen'])
        else:
            data = request.get_json()
            imagen_path = data.get('imagen')

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO proyecto
            (nombre, tipo_estudio, imagen, descripcion, fecha_inicio, fecha_fin, progreso, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            data.get('nombre'),
            data.get('tipo_estudio'),
            imagen_path,
            data.get('descripcion'),
            data.get('fecha_inicio'),
            data.get('fecha_fin'),
            data.get('progreso', 0),
            data.get('estado', 'planificacion')
        )
        cursor.execute(sql, valores)
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/proyectos/<int:id>', methods=['PUT'])
def actualizar_proyecto(id):
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen_path = None
            if 'imagen' in request.files:
                imagen_path = save_image(request.files['imagen'])
            else:
                imagen_path = data.get('imagen')
        else:
            data = request.get_json()
            imagen_path = data.get('imagen')

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE proyecto
            SET nombre=%s, tipo_estudio=%s, imagen=%s, descripcion=%s, fecha_inicio=%s,
                fecha_fin=%s, progreso=%s, estado=%s
            WHERE id=%s
        """
        valores = (
            data.get('nombre'),
            data.get('tipo_estudio'),
            imagen_path,
            data.get('descripcion'),
            data.get('fecha_inicio'),
            data.get('fecha_fin'),
            data.get('progreso', 0),
            data.get('estado', 'planificacion'),
            id
        )
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'mensaje': 'Proyecto actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/proyectos/<int:id>', methods=['DELETE'])
def eliminar_proyecto(id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # 1. Obtener la ruta de la imagen antes de eliminar el registro
        cursor.execute("SELECT imagen FROM proyecto WHERE id = %s", (id,))
        proyecto = cursor.fetchone()
        if not proyecto:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Proyecto no encontrado'}), 404

        imagen_path = proyecto.get('imagen')
        # 2. Eliminar el registro
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proyecto WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()

        # 3. Eliminar la imagen física si existe
        if imagen_path and os.path.isfile(imagen_path):
            try:
                os.remove(imagen_path)
            except Exception as img_err:
                # Si falla la eliminación de la imagen, solo lo reporta en el mensaje
                return jsonify({'mensaje': 'Proyecto eliminado, pero no se pudo borrar la imagen', 'error_imagen': str(img_err)}), 200

        return jsonify({'mensaje': 'Proyecto eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500