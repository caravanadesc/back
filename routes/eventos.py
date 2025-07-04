from flask import Blueprint, request, jsonify
from db import get_connection
import os
import uuid

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

# --- EVENTOS/NOTICIAS CRUD ---
@bp_eventos.route('/eventos-noticias', methods=['GET'])
def listar_eventos_noticias():
    # Filtros: q, tipo, fecha_desde, fecha_hasta
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        filtros = []
        valores = []
        q = request.args.get('q')
        tipo = request.args.get('tipo')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        if q:
            filtros.append("(titulo LIKE %s OR descripcion LIKE %s)")
            valores.extend([f"%{q}%", f"%{q}%"])
        if tipo and tipo != 'todos':
            filtros.append("tipo = %s")
            valores.append(tipo)
        if fecha_desde:
            filtros.append("fecha >= %s")
            valores.append(fecha_desde)
        if fecha_hasta:
            filtros.append("fecha <= %s")
            valores.append(fecha_hasta)
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"SELECT * FROM Evento_Noticia {where} ORDER BY fecha DESC"
        cursor.execute(sql, valores)
        eventos = cursor.fetchall()
        for evento in eventos:
            eid = evento['ID']
            # Asistentes
            cursor.execute("SELECT * FROM Evento_Asistente WHERE ID_evento = %s", (eid,))
            evento['asistentes'] = cursor.fetchall()
            # Áreas
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
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias/<int:id>', methods=['GET'])
def get_evento_noticia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Evento_Noticia WHERE ID = %s", (id,))
        evento = cursor.fetchone()
        if not evento:
            return jsonify({'error': 'No encontrado'}), 404
        cursor.execute("SELECT * FROM Evento_Asistente WHERE ID_evento = %s", (id,))
        evento['asistentes'] = cursor.fetchall()
        cursor.execute("""
            SELECT eai.ID_area, ai.nombre AS area_nombre
            FROM Evento_Area_Investigacion eai
            LEFT JOIN Area_Investigacion ai ON eai.ID_area = ai.ID
            WHERE eai.ID_evento = %s
        """, (id,))
        evento['areas_investigacion'] = cursor.fetchall()
        cursor.execute("SELECT * FROM Material_Evento WHERE ID_evento_noticia = %s", (id,))
        evento['materiales'] = cursor.fetchall()
        return jsonify(evento)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias', methods=['POST'])
def add_evento_noticia():
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

        required_fields = {
            'titulo': titulo,
            'descripcion': descripcion,
            'fecha': fecha,
            'lugar': lugar,
            'tipo': tipo,
            'fecha_creacion': fecha_creacion,
            'ID_usuario': ID_usuario
        }
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            msg = f"Faltan campos obligatorios: {', '.join(missing)}"
            print(f"[ERROR] error: {msg}", flush=True)
            return jsonify({'error': msg}), 400

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

@bp_eventos.route('/eventos-noticias/<int:id>', methods=['PUT'])
def update_evento_noticia(id):
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
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_eventos.route('/eventos-noticias/<int:id>', methods=['DELETE'])
def delete_evento_noticia(id):
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
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- ASISTENTES ---
@bp_eventos.route('/eventos-noticias/asistentes', methods=['POST'])
def add_asistente():
    data = request.get_json() or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Evento_Asistente (ID_evento, nombre_externo, email_externo, institucion_externa) VALUES (%s, %s, %s, %s)",
            (data.get('ID_evento'), data.get('nombre_externo'), data.get('email_externo'), data.get('institucion_externa'))
        )
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias/<int:ID_evento>/asistentes', methods=['DELETE'])
def remove_asistente(ID_evento):
    id_usuario = request.args.get('id_usuario')
    email_externo = request.args.get('email_externo')
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if id_usuario:
            cursor.execute("DELETE FROM Evento_Asistente WHERE ID_evento = %s AND ID_usuario = %s", (ID_evento, id_usuario))
        elif email_externo:
            cursor.execute("DELETE FROM Evento_Asistente WHERE ID_evento = %s AND email_externo = %s", (ID_evento, email_externo))
        else:
            return jsonify({'error': 'Falta id_usuario o email_externo'}), 400
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias/<int:ID_evento>/asistentes', methods=['GET'])
def get_asistentes_evento(ID_evento):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Evento_Asistente WHERE ID_evento = %s", (ID_evento,))
        asistentes = cursor.fetchall()
        return jsonify(asistentes)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- AREAS DE INVESTIGACION ---
@bp_eventos.route('/eventos-noticias/areas-investigacion', methods=['POST'])
def add_area():
    data = request.get_json() or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Evento_Area_Investigacion (ID_evento, ID_area) VALUES (%s, %s)",
            (data.get('ID_evento'), data.get('ID_area'))
        )
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias/<int:ID_evento>/areas-investigacion/<int:ID_area>', methods=['DELETE'])
def remove_area(ID_evento, ID_area):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Evento_Area_Investigacion WHERE ID_evento = %s AND ID_area = %s", (ID_evento, ID_area))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- MATERIALES ---
@bp_eventos.route('/eventos-noticias/<int:ID_evento>/materiales', methods=['POST'])
def add_material(ID_evento):
    # Recibe tipo, nombre y archivo (como multipart/form-data)
    if request.content_type.startswith('multipart/form-data'):
        tipo = request.form.get('tipo')
        nombre = request.form.get('nombre')
        archivo = None
        if 'archivo' in request.files:
            archivo = save_material(request.files['archivo'])
    else:
        data = request.get_json() or {}
        tipo = data.get('tipo')
        nombre = data.get('nombre')
        archivo = data.get('archivo')
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Material_Evento (ID_evento_noticia, tipo, nombre, archivo) VALUES (%s, %s, %s, %s)",
            (ID_evento, tipo, nombre, archivo)
        )
        conn.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_eventos.route('/eventos-noticias/<int:ID_evento>/materiales/<int:ID_material>', methods=['DELETE'])
def remove_material(ID_evento, ID_material):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT archivo FROM Material_Evento WHERE ID = %s AND ID_evento_noticia = %s", (ID_material, ID_evento))
        material = cursor.fetchone()
        if material and material['archivo']:
            delete_file(MATERIAL_FOLDER, material['archivo'])
        cursor.execute("DELETE FROM Material_Evento WHERE ID = %s AND ID_evento_noticia = %s", (ID_material, ID_evento))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()