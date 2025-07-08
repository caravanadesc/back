from flask import Blueprint, request, jsonify
from db import get_connection

bp_guias = Blueprint('guias', __name__)

# --- CRUD Guia_Tutorial ---
@bp_guias.route('/guias', methods=['GET'])
def listar_guias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Guia_Tutorial ORDER BY fecha_publicacion DESC")
        guias = cursor.fetchall()
        for guia in guias:
            gid = guia['ID']
            # Recursos
            cursor.execute("SELECT * FROM Guia_Recurso WHERE ID_guia = %s", (gid,))
            guia['recursos'] = cursor.fetchall()
            # Áreas de investigación
            cursor.execute("""
                SELECT gai.ID_area, ai.nombre AS area_nombre
                FROM Guia_Area_Investigacion gai
                LEFT JOIN Area_Investigacion ai ON gai.ID_area = ai.ID
                WHERE gai.ID_guia = %s
            """, (gid,))
            guia['areas_investigacion'] = cursor.fetchall()
        return jsonify(guias)
    except Exception as e:
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
        guia['recursos'] = cursor.fetchall()
        cursor.execute("""
            SELECT gai.ID_area, ai.nombre AS area_nombre
            FROM Guia_Area_Investigacion gai
            LEFT JOIN Area_Investigacion ai ON gai.ID_area = ai.ID
            WHERE gai.ID_guia = %s
        """, (id,))
        guia['areas_investigacion'] = cursor.fetchall()
        return jsonify(guia)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias', methods=['POST'])
def crear_guia():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json() or {}
        cursor.execute(
            "INSERT INTO Guia_Tutorial (titulo, descripcion, fecha_publicacion, ID_usuario) VALUES (%s, %s, %s, %s)",
            (data.get('titulo'), data.get('descripcion'), data.get('fecha_publicacion'), data.get('ID_usuario'))
        )
        guia_id = cursor.lastrowid

        # Recursos
        for recurso in data.get('recursos', []):
            cursor.execute(
                "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                (guia_id, recurso.get('tipo'), recurso.get('recurso'), recurso.get('descripcion'))
            )
        # Áreas de investigación
        for area in data.get('areas_investigacion', []):
            cursor.execute(
                "INSERT INTO Guia_Area_Investigacion (ID_guia, ID_area) VALUES (%s, %s)",
                (guia_id, area.get('ID_area'))
            )
        conn.commit()
        return jsonify({'id': guia_id}), 201
    except Exception as e:
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
        data = request.get_json() or {}
        cursor.execute(
            "UPDATE Guia_Tutorial SET titulo=%s, descripcion=%s, fecha_publicacion=%s, ID_usuario=%s WHERE ID=%s",
            (data.get('titulo'), data.get('descripcion'), data.get('fecha_publicacion'), data.get('ID_usuario'), id)
        )
        # Actualizar recursos
        if 'recursos' in data:
            cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
            for recurso in data['recursos']:
                cursor.execute(
                    "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
                    (id, recurso.get('tipo'), recurso.get('recurso'), recurso.get('descripcion'))
                )
        # Actualizar áreas de investigación
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
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>', methods=['DELETE'])
def eliminar_guia(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s", (id,))
        cursor.execute("DELETE FROM Guia_Area_Investigacion WHERE ID_guia = %s", (id,))
        cursor.execute("DELETE FROM Guia_Tutorial WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Guía eliminada'})
    except Exception as e:
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
        return jsonify(cursor.fetchall())
    except Exception as e:
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
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/recursos', methods=['POST'])
def add_recurso_guia(id):
    data = request.get_json() or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Guia_Recurso (ID_guia, tipo, recurso, descripcion) VALUES (%s, %s, %s, %s)",
            (id, data.get('tipo'), data.get('recurso'), data.get('descripcion'))
        )
        conn.commit()
        return jsonify({'mensaje': 'Recurso agregado'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_guias.route('/guias/<int:id>/recursos/<int:id_recurso>', methods=['DELETE'])
def delete_recurso_guia(id, id_recurso):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Guia_Recurso WHERE ID_guia = %s AND ID = %s", (id, id_recurso))
        conn.commit()
        return jsonify({'mensaje': 'Recurso eliminado'})
    except Exception as e:
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
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        