from flask import Blueprint, request, jsonify
from db import get_connection

bp_area = Blueprint('areainvestigacion', __name__)

@bp_area.route('/areas', methods=['GET'])
def listar_areas():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Area_Investigacion")
        areas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(areas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@bp_area.route('/areas/<int:id>', methods=['GET'])
def obtener_area(id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Area_Investigacion WHERE id = %s", (id,))
        area = cursor.fetchone()
        cursor.close()
        conn.close()
        if area:
            return jsonify(area)
        return jsonify({'error': 'Área no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@bp_area.route('/areas', methods=['POST'])
def crear_area():
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO Area_Investigacion (nombre, descripcion) VALUES (%s, %s)"
        cursor.execute(sql, (data.get('nombre'), data.get('descripcion')))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@bp_area.route('/areas/<int:id>', methods=['PUT'])
def actualizar_area(id):
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()
        sql = "UPDATE Area_Investigacion SET nombre=%s, descripcion=%s WHERE id=%s"
        cursor.execute(sql, (data.get('nombre'), data.get('descripcion'), id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'mensaje': 'Área actualizada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_area.route('/areas/<int:id>', methods=['DELETE'])
def eliminar_area(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Area_Investigacion WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'mensaje': 'Área eliminada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()