from flask import Blueprint, request, jsonify
from db import get_connection

bp_glosario = Blueprint('glosario', __name__)

@bp_glosario.route('/glosario', methods=['GET'])
def listar_glosario():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Glosario")
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_glosario.route('/glosario/<int:id>', methods=['GET'])
def obtener_glosario(id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Glosario WHERE ID = %s", (id,))
        item = cursor.fetchone()
        if item:
            return jsonify(item)
        return jsonify({'error': 'Término no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_glosario.route('/glosario', methods=['POST'])
def crear_glosario():
    try:
        data = request.get_json()
        termino = data.get('termino')
        descripcion = data.get('descripcion')
        fecha_creacion = data.get('fecha_creacion')
        id_usuario = data.get('ID_usuario')
        if not all([termino, descripcion, fecha_creacion, id_usuario]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO Glosario (termino, descripcion, fecha_creacion, ID_usuario) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (termino, descripcion, fecha_creacion, id_usuario))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_glosario.route('/glosario/<int:id>', methods=['PUT'])
def actualizar_glosario(id):
    try:
        data = request.get_json()
        termino = data.get('termino')
        descripcion = data.get('descripcion')
        fecha_creacion = data.get('fecha_creacion')
        id_usuario = data.get('ID_usuario')
        conn = get_connection()
        cursor = conn.cursor()
        sql = "UPDATE Glosario SET termino=%s, descripcion=%s, fecha_creacion=%s, ID_usuario=%s WHERE ID=%s"
        cursor.execute(sql, (termino, descripcion, fecha_creacion, id_usuario, id))
        conn.commit()
        return jsonify({'mensaje': 'Término actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp_glosario.route('/glosario/<int:id>', methods=['DELETE'])
def eliminar_glosario(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Glosario WHERE ID = %s", (id,))
        conn.commit()

        return jsonify({'mensaje': 'Término eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()