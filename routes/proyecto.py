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
        return filename
    return None

# --- PROYECTOS CRUD ---
@bp.route('/proyectos', methods=['GET'])
def listar_proyectos():
    conn = None
    cursor = None
    try:
        filtros = []
        valores = []
        campos = [
            'ID', 'nombre', 'tipo_estudio', 'imagen', 'descripcion',
            'fecha_inicio', 'fecha_fin', 'progreso', 'estado',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        q = request.args.get('q')
        if q:
            condiciones = [f"{campo} LIKE %s" for campo in campos if campo != 'ID' and campo != 'progreso']
            filtros.append("(" + " OR ".join(condiciones) + ")")
            valores.extend([f"%{q}%"] * len(condiciones))
        for campo in campos:
            valor = request.args.get(campo)
            if valor is not None:
                if campo in ['ID', 'progreso']:
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
        # Agrega áreas y colaboradores a cada proyecto
        for proyecto in resultados:
            pid = proyecto['ID']
            cursor.execute("""
                SELECT pai.ID_area, ai.nombre AS area_nombre
                FROM Proyecto_Area_Investigacion pai
                LEFT JOIN Area_Investigacion ai ON pai.ID_area = ai.ID
                WHERE pai.ID_proyecto = %s
            """, (pid,))
            proyecto['areas_investigacion'] = cursor.fetchall()
            cursor.execute("""
                SELECT pc.ID_usuario, u.nombre, u.apellido
                FROM Proyecto_Colaborador pc
                LEFT JOIN Usuario u ON pc.ID_usuario = u.ID
                WHERE pc.ID_proyecto = %s
            """, (pid,))
            proyecto['colaboradores'] = cursor.fetchall()
        return jsonify(resultados)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp.route('/proyectos/<int:id>', methods=['GET'])
def obtener_proyecto(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Proyecto WHERE ID = %s", (id,))
        proyecto = cursor.fetchone()
        if not proyecto:
            return jsonify({'error': 'Proyecto no encontrado'}), 404
        # Áreas de investigación
        cursor.execute("""
            SELECT pai.ID_area, ai.nombre AS area_nombre
            FROM Proyecto_Area_Investigacion pai
            LEFT JOIN Area_Investigacion ai ON pai.ID_area = ai.ID
            WHERE pai.ID_proyecto = %s
        """, (id,))
        proyecto['areas_investigacion'] = cursor.fetchall()
        # Colaboradores
        cursor.execute("""
            SELECT pc.ID_usuario, u.nombre, u.apellido
            FROM Proyecto_Colaborador pc
            LEFT JOIN Usuario u ON pc.ID_usuario = u.ID
            WHERE pc.ID_proyecto = %s
        """, (id,))
        proyecto['colaboradores'] = cursor.fetchall()
        return jsonify(proyecto)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
import json
# ...resto de imports...

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
            data = request.get_json() or {}
            imagen_path = data.get('imagen')

        # --- CORRECCIÓN: decodifica los campos JSON si vienen como string ---
        areas = data.get('areas_investigacion', [])
        if isinstance(areas, str):
            areas = json.loads(areas)
        colabs = data.get('colaboradores', [])
        if isinstance(colabs, str):
            colabs = json.loads(colabs)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO Proyecto
            (nombre, tipo_estudio, imagen, descripcion, fecha_inicio, fecha_fin, progreso, estado, fecha_creacion, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            data.get('fecha_creacion'),
            data.get('fecha_actualizacion')
        )
        cursor.execute(sql, valores)
        new_id = cursor.lastrowid

        # Áreas de investigación
        for area in areas:
            cursor.execute(
                "INSERT INTO Proyecto_Area_Investigacion (ID_proyecto, ID_area) VALUES (%s, %s)",
                (new_id, area.get('ID_area'))
            )
        # Colaboradores
        for colab in colabs:
            cursor.execute(
                "INSERT INTO Proyecto_Colaborador (ID_proyecto, ID_usuario) VALUES (%s, %s)",
                (new_id, colab.get('ID_usuario'))
            )

        conn.commit()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        print(f"[ERROR] error: {e}", flush=True)
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
            data = request.get_json() or {}
            imagen_path = data.get('imagen')

        # --- CORRECCIÓN: decodifica los campos JSON si vienen como string ---
        areas = data.get('areas_investigacion', [])
        if isinstance(areas, str):
            areas = json.loads(areas)
        colabs = data.get('colaboradores', [])
        if isinstance(colabs, str):
            colabs = json.loads(colabs)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE Proyecto
            SET nombre=%s, tipo_estudio=%s, imagen=%s, descripcion=%s, fecha_inicio=%s,
                fecha_fin=%s, progreso=%s, estado=%s, fecha_creacion=%s, fecha_actualizacion=%s
            WHERE ID=%s
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
            data.get('fecha_creacion'),
            data.get('fecha_actualizacion'),
            id
        )
        cursor.execute(sql, valores)

        # Actualizar áreas de investigación
        cursor.execute("DELETE FROM Proyecto_Area_Investigacion WHERE ID_proyecto = %s", (id,))
        for area in areas:
            cursor.execute(
                "INSERT INTO Proyecto_Area_Investigacion (ID_proyecto, ID_area) VALUES (%s, %s)",
                (id, area.get('ID_area'))
            )
        # Actualizar colaboradores
        cursor.execute("DELETE FROM Proyecto_Colaborador WHERE ID_proyecto = %s", (id,))
        for colab in colabs:
            cursor.execute(
                "INSERT INTO Proyecto_Colaborador (ID_proyecto, ID_usuario) VALUES (%s, %s)",
                (id, colab.get('ID_usuario'))
            )

        conn.commit()
        return jsonify({'mensaje': 'Proyecto actualizado'})
    except Exception as e:
        if conn: conn.rollback()
        print(f"[ERROR] error: {e}", flush=True)
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
        cursor.execute("SELECT imagen FROM Proyecto WHERE ID = %s", (id,))
        proyecto = cursor.fetchone()
        if not proyecto:
            return jsonify({'error': 'Proyecto no encontrado'}), 404

        imagen_nombre = proyecto.get('imagen')
        # 2. Eliminar relaciones
        cursor.execute("DELETE FROM Proyecto_Area_Investigacion WHERE ID_proyecto = %s", (id,))
        cursor.execute("DELETE FROM Proyecto_Colaborador WHERE ID_proyecto = %s", (id,))
        # 3. Eliminar el registro principal
        cursor.execute("DELETE FROM Proyecto WHERE ID = %s", (id,))
        conn.commit()

        # 4. Eliminar la imagen física si existe
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
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- ENDPOINTS PARA AREAS Y COLABORADORES INDIVIDUALES ---
# Obtener áreas de un proyecto
@bp.route('/proyectos/<int:id>/areas-investigacion', methods=['GET'])
def get_areas_proyecto(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT pai.ID_area, ai.nombre AS area_nombre
            FROM Proyecto_Area_Investigacion pai
            LEFT JOIN Area_Investigacion ai ON pai.ID_area = ai.ID
            WHERE pai.ID_proyecto = %s
        """, (id,))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Agregar un área a un proyecto
@bp.route('/proyectos/<int:id>/areas-investigacion', methods=['POST'])
def add_area_proyecto(id):
    data = request.get_json() or {}
    id_area = data.get('ID_area')
    if not id_area:
        return jsonify({'error': 'ID_area es requerido'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Proyecto_Area_Investigacion (ID_proyecto, ID_area) VALUES (%s, %s)",
            (id, id_area)
        )
        conn.commit()
        return jsonify({'mensaje': 'Área agregada'}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Eliminar un área de un proyecto
@bp.route('/proyectos/<int:id>/areas-investigacion/<int:id_area>', methods=['DELETE'])
def delete_area_proyecto(id, id_area):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM Proyecto_Area_Investigacion WHERE ID_proyecto = %s AND ID_area = %s",
            (id, id_area)
        )
        conn.commit()
        return jsonify({'mensaje': 'Área eliminada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)                
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Obtener colaboradores de un proyecto
@bp.route('/proyectos/<int:id>/colaboradores', methods=['GET'])
def get_colaboradores_proyecto(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT pc.ID_usuario, u.nombre, u.apellido
            FROM Proyecto_Colaborador pc
            LEFT JOIN Usuario u ON pc.ID_usuario = u.ID
            WHERE pc.ID_proyecto = %s
        """, (id,))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Agregar un colaborador a un proyecto
@bp.route('/proyectos/<int:id>/colaboradores', methods=['POST'])
def add_colaborador_proyecto(id):
    data = request.get_json() or {}
    id_usuario = data.get('ID_usuario')
    if not id_usuario:
        return jsonify({'error': 'ID_usuario es requerido'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Proyecto_Colaborador (ID_proyecto, ID_usuario) VALUES (%s, %s)",
            (id, id_usuario)
        )
        conn.commit()
        return jsonify({'mensaje': 'Colaborador agregado'}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Eliminar un colaborador de un proyecto
@bp.route('/proyectos/<int:id>/colaboradores/<int:id_usuario>', methods=['DELETE'])
def delete_colaborador_proyecto(id, id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM Proyecto_Colaborador WHERE ID_proyecto = %s AND ID_usuario = %s",
            (id, id_usuario)
        )
        conn.commit()
        return jsonify({'mensaje': 'Colaborador eliminado'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()