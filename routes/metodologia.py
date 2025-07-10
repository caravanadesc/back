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

@bp_metodologia.route('/metodologias', methods=['GET'])
def listar_metodologias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Metodologia_Prueba ORDER BY fecha_creacion DESC")
        metodologias = cursor.fetchall()
        for m in metodologias:
            if m.get('imagen'):
                m['imagen_url'] = f"/uploads/metodologia/{m['imagen']}"
        return jsonify(metodologias)
    except Exception as e:
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
        return jsonify(metodologia)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_metodologia.route('/metodologias', methods=['POST'])
def crear_metodologia():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = None
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_image(request.files['imagen'])
            else:
                imagen = None
            cursor.execute(
                "INSERT INTO Metodologia_Prueba (nombre, descripcion, imagen, tipo, fecha_creacion, `Textos completos`) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    data.get('nombre'),
                    data.get('descripcion'),
                    imagen,
                    data.get('tipo'),
                    data.get('fecha_creacion'),
                    data.get('Textos completos')
                )
            )
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen')
            cursor.execute(
                "INSERT INTO Metodologia_Prueba (nombre, descripcion, imagen, tipo, fecha_creacion, `Textos completos`) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    data.get('nombre'),
                    data.get('descripcion'),
                    imagen,
                    data.get('tipo'),
                    data.get('fecha_creacion'),
                    data.get('Textos completos')
                )
            )
        conn.commit()
        return jsonify({'id': cursor.lastrowid}), 201
    except Exception as e:
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

        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            imagen = imagen_actual
            if 'imagen' in request.files and request.files['imagen'].filename:
                imagen = save_image(request.files['imagen'])
        else:
            data = request.get_json() or {}
            imagen = data.get('imagen', imagen_actual)

        cursor.execute(
            "UPDATE Metodologia_Prueba SET nombre=%s, descripcion=%s, imagen=%s, tipo=%s, fecha_creacion=%s, `Textos completos`=%s WHERE ID=%s",
            (
                data.get('nombre'),
                data.get('descripcion'),
                imagen,
                data.get('tipo'),
                data.get('fecha_creacion'),
                data.get('Textos completos'),
                id
            )
        )
        conn.commit()
        return jsonify({'mensaje': 'Metodología actualizada'})
    except Exception as e:
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
        cursor.execute("DELETE FROM Metodologia_Prueba WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Metodología eliminada'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()