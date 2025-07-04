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
        return filename  # Solo el nombre del archivo
    return None

@bp.route('/proyectos', methods=['GET'])
def listar_proyectos():
    conn = None
    cursor = None
    try:
        filtros = []
        valores = []
        campos = [
            'id', 'nombre', 'tipo_estudio', 'imagen', 'descripcion',
            'fecha_inicio', 'fecha_fin', 'progreso', 'estado',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        q = request.args.get('q')
        if q:
            condiciones = [f"{campo} LIKE %s" for campo in campos if campo != 'id' and campo != 'progreso']
            filtros.append("(" + " OR ".join(condiciones) + ")")
            valores.extend([f"%{q}%"] * len(condiciones))
        for campo in campos:
            valor = request.args.get(campo)
            if valor is not None:
                if campo in ['id', 'progreso']:
                    filtros.append(f"{campo} = %s")
                    valores.append(valor)
                else:
                    filtros.append(f"{campo} LIKE %s")
                    valores.append(f"%{valor}%")
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"SELECT * FROM Proyecto {where}"

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, valores)
        resultados = cursor.fetchall()
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp.route('/proyectos', methods=['POST'])
def crear_proyecto():
    conn = None
    cursor = None
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
            INSERT INTO Proyecto
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
        return jsonify({'id': new_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp.route('/proyectos/<int:id>', methods=['PUT'])
def actualizar_proyecto(id):
    conn = None
    cursor = None
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
            UPDATE Proyecto
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
        return jsonify({'mensaje': 'Proyecto actualizado'})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp.route('/proyectos/<int:id>', methods=['DELETE'])
def eliminar_proyecto(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # 1. Obtener la ruta de la imagen antes de eliminar el registro
        cursor.execute("SELECT imagen FROM Proyecto WHERE id = %s", (id,))
        proyecto = cursor.fetchone()
        if not proyecto:
            return jsonify({'error': 'Proyecto no encontrado'}), 404

        imagen_nombre = proyecto.get('imagen')
        # 2. Eliminar el registro
        cursor.execute("DELETE FROM Proyecto WHERE id = %s", (id,))
        conn.commit()

        # 3. Eliminar la imagen física si existe
        if imagen_nombre:
            file_path = os.path.join(UPLOAD_FOLDER, imagen_nombre)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as img_err:
                    return jsonify({'mensaje': 'Proyecto eliminado, pero no se pudo borrar la imagen', 'error_imagen': str(img_err)}), 200

        return jsonify({'mensaje': 'Proyecto eliminado'})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()