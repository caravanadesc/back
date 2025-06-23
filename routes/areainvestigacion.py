from flask import Blueprint, request, jsonify
from db import get_connection

bp_area = Blueprint('areainvestigacion', __name__)

@bp_area.route('/areas', methods=['GET'])
def listar_areas():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Area_Investigacion")
        areas = cursor.fetchall()
        return jsonify(areas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_area.route('/areas/<int:id>', methods=['GET'])
def obtener_area(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Area_Investigacion WHERE id = %s", (id,))
        area = cursor.fetchone()
        if area:
            return jsonify(area)
        return jsonify({'error': 'Área no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_area.route('/areas', methods=['POST'])
def crear_area():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO Area_Investigacion (nombre, descripcion) VALUES (%s, %s)"
        cursor.execute(sql, (data.get('nombre'), data.get('descripcion')))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_area.route('/areas/<int:id>', methods=['PUT'])
def actualizar_area(id):
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()
        sql = "UPDATE Area_Investigacion SET nombre=%s, descripcion=%s WHERE id=%s"
        cursor.execute(sql, (data.get('nombre'), data.get('descripcion'), id))
        conn.commit()
        return jsonify({'mensaje': 'Área actualizada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_area.route('/areas/<int:id>', methods=['DELETE'])
def eliminar_area(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Area_Investigacion WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Área eliminada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()