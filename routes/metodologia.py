from flask import Blueprint, request, jsonify
from db import get_connection
import os
import uuid

bp_metodologia = Blueprint('metodologia', __name__)

UPLOAD_FOLDER = 'src/uploads/metodologia'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def save_image(file):
    if not file or not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(file_path)
    return unique_name

def get_caracteristicas(conn, metodologia_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Metodologia_Caracteristica WHERE ID_metodologia = %s", (metodologia_id,))
    return cursor.fetchall()

# --- Metodologia_Prueba CRUD ---
@bp_metodologia.route('/metodologias', methods=['GET'])
def listar_metodologias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        filtros = []
        valores = []
        for campo in ['nombre', 'tipo', 'fecha_creacion']:
            valor = request.args.get(campo)
            if valor:
                filtros.append(f"{campo} LIKE %s")
                valores.append(f"%{valor}%")
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        cursor.execute(f"SELECT * FROM Metodologia_Prueba {where} ORDER BY fecha_creacion DESC", valores)
        metodologias = cursor.fetchall()
        for m in metodologias:
            if m.get('imagen'):
                m['imagen_url'] = f"/uploads/metodologia/{m['imagen']}"
            m['caracteristicas'] = get_caracteristicas(conn, m['ID'])
        return jsonify(metodologias)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/metodologias/<int:id>', methods=['GET'])
def obtener_metodologia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Metodologia_Prueba WHERE ID = %s", (id,))
        metodologia = cursor.fetchone()
        if not metodologia:
            return jsonify({'error': 'No encontrada'}), 404
        if metodologia.get('imagen'):
            metodologia['imagen_url'] = f"/uploads/metodologia/{metodologia['imagen']}"
        metodologia['caracteristicas'] = get_caracteristicas(conn, metodologia['ID'])
        return jsonify(metodologia)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/metodologias', methods=['POST'])
def crear_metodologia():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        imagen = None
        caracteristicas = []
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_image(request.files['imagen'])
            if 'caracteristicas' in data:
                import json
                caracteristicas = json.loads(data.get('caracteristicas'))
            cursor.execute(
                "INSERT INTO Metodologia_Prueba (nombre, descripcion, imagen, tipo, fecha_creacion) VALUES (%s, %s, %s, %s, %s)",
                (
                    data.get('nombre'),
                    data.get('descripcion'),
                    imagen,
                    data.get('tipo'),
                    data.get('fecha_creacion')
                )
            )
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen')
            caracteristicas = data.get('caracteristicas', [])
            cursor.execute(
                "INSERT INTO Metodologia_Prueba (nombre, descripcion, imagen, tipo, fecha_creacion) VALUES (%s, %s, %s, %s, %s)",
                (
                    data.get('nombre'),
                    data.get('descripcion'),
                    imagen,
                    data.get('tipo'),
                    data.get('fecha_creacion')
                )
            )
        metodologia_id = cursor.lastrowid
        # Insertar características si vienen
        for c in caracteristicas:
            cursor.execute(
                "INSERT INTO Metodologia_Caracteristica (ID_metodologia, caracteristica, descripcion) VALUES (%s, %s, %s)",
                (metodologia_id, c.get('caracteristica'), c.get('descripcion'))
            )
        conn.commit()
        return jsonify({'id': metodologia_id}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/metodologias/<int:id>', methods=['PUT'])
def actualizar_metodologia(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT imagen FROM Metodologia_Prueba WHERE ID=%s", (id,))
        actual = cursor.fetchone()
        imagen_actual = actual[0] if actual else None

        caracteristicas = []
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = imagen_actual
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_image(request.files['imagen'])
            if 'caracteristicas' in data:
                import json
                caracteristicas = json.loads(data.get('caracteristicas'))
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen', imagen_actual)
            caracteristicas = data.get('caracteristicas', [])

        cursor.execute(
            "UPDATE Metodologia_Prueba SET nombre=%s, descripcion=%s, imagen=%s, tipo=%s, fecha_creacion=%s WHERE ID=%s",
            (
                data.get('nombre'),
                data.get('descripcion'),
                imagen,
                data.get('tipo'),
                data.get('fecha_creacion'),
                id
            )
        )
        # Actualizar características: eliminar todas y volver a insertar si vienen
        if isinstance(caracteristicas, list):
            cursor.execute("DELETE FROM Metodologia_Caracteristica WHERE ID_metodologia = %s", (id,))
            for c in caracteristicas:
                cursor.execute(
                    "INSERT INTO Metodologia_Caracteristica (ID_metodologia, caracteristica, descripcion) VALUES (%s, %s, %s)",
                    (id, c.get('caracteristica'), c.get('descripcion'))
                )
        conn.commit()
        return jsonify({'mensaje': 'Metodología actualizada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/metodologias/<int:id>', methods=['DELETE'])
def eliminar_metodologia(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT imagen FROM Metodologia_Prueba WHERE ID = %s", (id,))
        img_row = cursor.fetchone()
        if img_row and img_row['imagen']:
            img_path = os.path.join(UPLOAD_FOLDER, img_row['imagen'])
            if os.path.isfile(img_path):
                os.remove(img_path)
        cursor.execute("DELETE FROM Metodologia_Caracteristica WHERE ID_metodologia = %s", (id,))
        cursor.execute("DELETE FROM Metodologia_Prueba WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Metodología eliminada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Metodologia_Caracteristica CRUD individual ---
@bp_metodologia.route('/caracteristicas', methods=['GET'])
def listar_caracteristicas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Metodologia_Caracteristica ORDER BY ID DESC")
        caracteristicas = cursor.fetchall()
        return jsonify(caracteristicas)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/caracteristicas/<int:id>', methods=['GET'])
def obtener_caracteristica(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Metodologia_Caracteristica WHERE ID = %s", (id,))
        caracteristica = cursor.fetchone()
        if not caracteristica:
            return jsonify({'error': 'No encontrada'}), 404
        return jsonify(caracteristica)
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/caracteristicas', methods=['POST'])
def crear_caracteristica():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json() or {}
        cursor.execute(
            "INSERT INTO Metodologia_Caracteristica (ID_metodologia, caracteristica, descripcion) VALUES (%s, %s, %s)",
            (
                data.get('ID_metodologia'),
                data.get('caracteristica'),
                data.get('descripcion')
            )
        )
        conn.commit()
        return jsonify({'id': cursor.lastrowid}), 201
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/caracteristicas/<int:id>', methods=['PUT'])
def actualizar_caracteristica(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json() or {}
        cursor.execute(
            "UPDATE Metodologia_Caracteristica SET ID_metodologia=%s, caracteristica=%s, descripcion=%s WHERE ID=%s",
            (
                data.get('ID_metodologia'),
                data.get('caracteristica'),
                data.get('descripcion'),
                id
            )
        )
        conn.commit()
        return jsonify({'mensaje': 'Característica actualizada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/caracteristicas/<int:id>', methods=['DELETE'])
def eliminar_caracteristica(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Metodologia_Caracteristica WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Característica eliminada'})
    except Exception as e:
        print(f"[ERROR] error: {e}", flush=True)
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()