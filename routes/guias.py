from flask import Blueprint, request, jsonify
from db import get_connection
import os
import uuid
from werkzeug.utils import secure_filename

bp_guias = Blueprint('guias', __name__)

UPLOAD_FOLDER = 'src/uploads/guias'
RECURSO_FOLDER = 'src/uploads/tutoriales'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'mp4', 'mov', 'avi'} | ALLOWED_IMAGE_EXTENSIONS

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def save_file(file, folder, allowed):
    if not file:
        print("[ERROR] No se recibió archivo para guardar.", flush=True)
        return None
    if not allowed_file(file.filename, allowed):
        print(f"[ERROR] Archivo con extensión no permitida: {file.filename}", flush=True)
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, unique_name)
    try:
        file.save(file_path)
        print(f"[INFO] Archivo guardado: {unique_name} en {file_path}", flush=True)
        return unique_name
    except Exception as e:
        print(f"[ERROR] No se pudo guardar el archivo {file.filename}: {e}", flush=True)
        return None

# --- CRUD Guia_Tutorial ---
@bp_guias.route('/guias', methods=['GET'])
def listar_guias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        filtros = []
        valores = []
        # Filtros posibles
        for campo in ['titulo', 'descripcion', 'categoria', 'ID_usuario']:
            valor = request.args.get(campo)
            if valor:
                filtros.append(f"{campo} LIKE %s")
                valores.append(f"%{valor}%")
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        if fecha_desde:
            filtros.append("fecha_publicacion >= %s")
            valores.append(fecha_desde)
        if fecha_hasta:
            filtros.append("fecha_publicacion <= %s")
            valores.append(fecha_hasta)
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"SELECT * FROM Guia_Tutorial {where} ORDER BY fecha_publicacion DESC"
        cursor.execute(sql, valores)
        guias = cursor.fetchall()
        for guia in guias:
            gid = guia['ID']
            # Recursos
            cursor.execute("SELECT * FROM Guia_Recurso WHERE ID_guia = %s", (gid,))
            recursos = cursor.fetchall()
            for r in recursos:
                if r['tipo'] in ALLOWED_IMAGE_EXTENSIONS or r['tipo'] in ALLOWED_FILE_EXTENSIONS:
                    r['recurso_url'] = f"/uploads/tutoriales/{r['recurso']}" if r['recurso'] else None
            guia['recursos'] = recursos
            # Áreas de investigación
            cursor.execute("""
                SELECT gai.ID_area, ai.nombre AS area_nombre
                FROM Guia_Area_Investigacion gai
                LEFT JOIN Area_Investigacion ai ON gai.ID_area = ai.ID
                WHERE gai.ID_guia = %s
            """, (gid,))
            guia['areas_investigacion'] = cursor.fetchall()
            # Imagen URL
            if guia.get('imagen'):
                guia['imagen_url'] = f"/uploads/{guia['imagen']}"
        return jsonify(guias)
    except Exception as e:  
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>', methods=['GET'])
def obtener_guia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Guia_Tutorial WHERE ID = %s", (id,))
        guia = cursor.fetchone()
        if not guia:
            return jsonify({'error': 'Guía no encontrada'}), 404
        cursor.execute("SELECT * FROM Guia_Recurso WHERE ID_guia = %s", (id,))
        recursos = cursor.fetchall()
        for r in recursos:
            if r['tipo'] in ALLOWED_IMAGE_EXTENSIONS or r['tipo'] in ALLOWED_FILE_EXTENSIONS:
                r['recurso_url'] = f"/uploads/tutoriales/{r['recurso']}" if r['recurso'] else None
        guia['recursos'] = recursos
        cursor.execute("""
            SELECT gai.ID_area, ai.nombre AS area_nombre
            FROM Guia_Area_Investigacion gai
            LEFT JOIN Area_Investigacion ai ON gai.ID_area = ai.ID
            WHERE gai.ID_guia = %s
        """, (id,))
        guia['areas_investigacion'] = cursor.fetchall()
        if guia.get('imagen'):
            guia['imagen_url'] = f"/uploads/{guia['imagen']}"
        return jsonify(guia)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias', methods=['POST'])
def crear_guia():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        recursos = []
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = None
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_file(request.files['imagen'], UPLOAD_FOLDER, ALLOWED_IMAGE_EXTENSIONS)
                if not imagen:
                    print(f"[ERROR] No se pudo guardar la imagen: {request.files['imagen'].filename}", flush=True)
            else:
                print("[INFO] No se recibió imagen en el formulario.", flush=True)

            # --- AQUÍ: Manejo de recurso como archivo único ---
            if 'recurso' in request.files and request.files['recurso'].filename:
                archivo = save_file(request.files['recurso'], RECURSO_FOLDER, ALLOWED_FILE_EXTENSIONS)
                if archivo:
                    tipo = data.get('tipo', request.files['recurso'].mimetype.split('/')[-1])
                    descripcion = data.get('descripcion', '')
                    recursos.append({'tipo': tipo, 'recurso': archivo, 'descripcion': descripcion})
            # --- Manejo de recurso como link único (en form) ---
            elif 'recurso' in data and data.get('recurso'):
                tipo = data.get('tipo', 'link')
                recurso = data.get('recurso')
                descripcion = data.get('descripcion', '')
                recursos.append({'tipo': tipo, 'recurso': recurso, 'descripcion': descripcion})
            # --- Manejo de recursos como lista (poco común en form) ---
            elif 'recursos' in data:
                recursos = data.getlist('recursos')
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen')
            if not imagen:
                print("[INFO] No se recibió imagen en el JSON.", flush=True)
            recursos = []
            if 'recursos' in data:
                recursos = data['recursos']
                if isinstance(recursos, dict):
                    recursos = [recursos]
            elif 'recurso' in data and data.get('recurso'):
                recursos = [{
                    'tipo': data.get('tipo', 'link'),
                    'recurso': data.get('recurso'),
                    'descripcion': data.get('descripcion', '')
                }]

        cursor.execute(
            "INSERT INTO Guia_Tutorial (titulo, descripcion, fecha_publicacion, ID_usuario, categoria, imagen) VALUES (%s, %s, %s, %s, %s, %s)",
            (data.get('titulo'), data.get('descripcion'), data.get('fecha_publicacion'), data.get('ID_usuario'), data.get('categoria'), imagen)
        )
        guia_id = cursor.lastrowid

        for recurso in recursos:
            archivo = recurso.get('recurso')
            tipo = recurso.get('tipo', 'link')
            descripcion = recurso.get('descripcion', '')
            if archivo:
                cursor.execute(
                    "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                    (guia_id, tipo, archivo, descripcion)
                )
        for area in data.get('areas_investigacion', []):
            cursor.execute(
                "INSERT INTO Guia_Area_Investigacion (ID_guia, ID_area) VALUES (%s, %s)",
                (guia_id, area.get('ID_area'))
            )
        conn.commit()
        return jsonify({'id': guia_id}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>', methods=['PUT'])
def actualizar_guia(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Obtener datos actuales de la guía
        cursor.execute("SELECT imagen FROM Guia_Tutorial WHERE ID=%s", (id,))
        guia_actual = cursor.fetchone()
        imagen_actual = guia_actual[0] if guia_actual else None

        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = imagen_actual
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_file(request.files['imagen'], UPLOAD_FOLDER, ALLOWED_IMAGE_EXTENSIONS)
                if not imagen:
                    print(f"[ERROR] No se pudo guardar la imagen: {request.files['imagen'].filename}", flush=True)
            else:
                print("[INFO] No se recibió imagen nueva, se mantiene la anterior.", flush=True)
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen', imagen_actual)

        # Construir el query dinámicamente para no actualizar imagen si no corresponde
        campos = [
            "titulo=%s",
            "descripcion=%s",
            "fecha_publicacion=%s",
            "ID_usuario=%s",
            "categoria=%s"
        ]
        valores = [
            data.get('titulo'),
            data.get('descripcion'),
            data.get('fecha_publicacion'),
            data.get('ID_usuario'),
            data.get('categoria')
        ]
        if imagen != imagen_actual:
            campos.append("imagen=%s")
            valores.append(imagen)
        valores.append(id)
        sql = f"UPDATE Guia_Tutorial SET {', '.join(campos)} WHERE ID=%s"
        cursor.execute(sql, valores)

        # --- Recursos: solo si llegan ---
        recursos_actualizados = False

        if request.content_type.startswith('multipart/form-data'):
            # Si llega archivo
            if 'recurso' in request.files and request.files['recurso'].filename:
                cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
                archivo = save_file(request.files['recurso'], RECURSO_FOLDER, ALLOWED_FILE_EXTENSIONS)
                if archivo:
                    tipo = data.get('tipo', request.files['recurso'].mimetype.split('/')[-1])
                    descripcion = data.get('descripcion', '')
                    cursor.execute(
                        "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                        (id, tipo, archivo, descripcion)
                    )
                    recursos_actualizados = True
            # Si llega link como recurso (en form)
            elif 'recurso' in data and data.get('recurso'):
                cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
                tipo = data.get('tipo', 'link')
                recurso = data.get('recurso')
                descripcion = data.get('descripcion', '')
                cursor.execute(
                    "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                    (id, tipo, recurso, descripcion)
                )
                recursos_actualizados = True
        elif 'recursos' in data:
            cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
            recursos = data['recursos']
            if isinstance(recursos, dict):
                recursos = [recursos]
            for recurso in recursos:
                archivo = recurso.get('recurso')
                tipo = recurso.get('tipo', 'link')
                descripcion = recurso.get('descripcion', '')
                if archivo:
                    cursor.execute(
                        "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                        (id, tipo, archivo, descripcion)
                    )
                    recursos_actualizados = True
        elif 'recurso' in data and data.get('recurso'):
            cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
            tipo = data.get('tipo', 'link')
            recurso = data.get('recurso')
            descripcion = data.get('descripcion', '')
            cursor.execute(
                "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                (id, tipo, recurso, descripcion)
            )
            recursos_actualizados = True

        # Áreas de investigación: solo si llegan
        if 'areas_investigacion' in data:
            cursor.execute("DELETE FROM Guia_Area_Investigacion WHERE ID_guia = %s", (id,))
            for area in data['areas_investigacion']:
                cursor.execute(
                    "INSERT INTO Guia_Area_Investigacion (ID_guia, ID_area) VALUES (%s, %s)",
                    (id, area.get('ID_area'))
                )

        conn.commit()
        return jsonify({'mensaje': 'Guía actualizada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>', methods=['DELETE'])
def eliminar_guia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Eliminar archivos físicos de recursos e imagen
        cursor.execute("SELECT recurso FROM Guia_Recurso WHERE ID_guia = %s", (id,))
        for row in cursor.fetchall():
            if row['recurso']:
                file_path = os.path.join(RECURSO_FOLDER, row['recurso'])
                if os.path.isfile(file_path):
                    os.remove(file_path)
        cursor.execute("SELECT imagen FROM Guia_Tutorial WHERE ID = %s", (id,))
        img_row = cursor.fetchone()
        if img_row and img_row['imagen']:
            img_path = os.path.join(UPLOAD_FOLDER, img_row['imagen'])
            if os.path.isfile(img_path):
                os.remove(img_path)
        cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
        cursor.execute("DELETE FROM Guia_Area_Investigacion WHERE ID_guia = %s", (id,))
        cursor.execute("DELETE FROM Guia_Tutorial WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Guía eliminada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- ENDPOINTS INDIVIDUALES PARA RECURSOS Y ÁREAS ---
@bp_guias.route('/guias/<int:id>/recursos', methods=['GET'])
def get_recursos_guia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Guia_Recurso WHERE ID_guia = %s", (id,))
        recursos = cursor.fetchall()
        for r in recursos:
            if r['tipo'] in ALLOWED_IMAGE_EXTENSIONS or r['tipo'] in ALLOWED_FILE_EXTENSIONS:
                r['recurso_url'] = f"/uploads/tutoriales/{r['recurso']}" if r['recurso'] else None
        return jsonify(recursos)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/areas-investigacion', methods=['GET'])
def get_areas_guia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT gai.ID_area, ai.nombre AS area_nombre
            FROM Guia_Area_Investigacion gai
            LEFT JOIN Area_Investigacion ai ON gai.ID_area = ai.ID
            WHERE gai.ID_guia = %s
        """, (id,))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/recursos', methods=['POST'])
def add_recurso_guia(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if request.content_type.startswith('multipart/form-data'):
            tipo = request.form.get('tipo')
            descripcion = request.form.get('descripcion')
            archivo = None
            if 'archivo' in request.files:
                archivo = save_file(request.files['archivo'], RECURSO_FOLDER, ALLOWED_FILE_EXTENSIONS)
            recurso = archivo
        else:
            data = request.get_json() or {}
            tipo = data.get('tipo')
            descripcion = data.get('descripcion')
            recurso = data.get('recurso')
        cursor.execute(
            "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
            (id, tipo, recurso, descripcion)
        )
        conn.commit()
        return jsonify({'mensaje': 'Recurso agregado'}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/recursos/<int:id_recurso>', methods=['DELETE'])
def delete_recurso_guia(id, id_recurso):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT recurso, tipo FROM Guia_Recurso WHERE ID_guia = %s AND ID = %s", (id, id_recurso))
        row = cursor.fetchone()
        if row and row['recurso']:
            file_path = os.path.join(RECURSO_FOLDER, row['recurso'])
            if os.path.isfile(file_path):
                os.remove(file_path)
        cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s AND ID = %s", (id, id_recurso))
        conn.commit()
        return jsonify({'mensaje': 'Recurso eliminado'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/areas-investigacion', methods=['POST'])
def add_area_guia(id):
    data = request.get_json() or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Guia_Area_Investigacion (ID_guia, ID_area) VALUES (%s, %s)",
            (id, data.get('ID_area'))
        )
        conn.commit()
        return jsonify({'mensaje': 'Área agregada'}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/areas-investigacion/<int:id_area>', methods=['DELETE'])
def delete_area_guia(id, id_area):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Guia_Area_Investigacion WHERE ID_guia = %s AND ID_area = %s", (id, id_area))
        conn.commit()
        return jsonify({'mensaje': 'Área eliminada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
