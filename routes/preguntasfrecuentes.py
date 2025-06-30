from flask import Blueprint, request, jsonify
from db import get_connection

bp_preguntas = Blueprint('preguntasfrecuentes', __name__)

@bp_preguntas.route('/preguntasfrecuentes', methods=['GET'])
def listar_preguntas():
    conn = None
    cursor = None
    try:
        filtros = []
        valores = []
        # Campos que puedes filtrar
        campos_filtrables = ['pregunta', 'respuesta', 'orden', 'fecha_creacion', 'fecha_actualizacion']

        for campo in campos_filtrables:
            valor = request.args.get(campo)
            if valor is not None:
                filtros.append(f"{campo} = %s")
                valores.append(valor)

        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"SELECT * FROM Pregunta_Frecuente {where} ORDER BY orden ASC"

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, valores)
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_preguntas.route('/preguntasfrecuentes/<int:id>', methods=['GET'])
def obtener_pregunta(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Pregunta_Frecuente WHERE ID = %s", (id,))
        item = cursor.fetchone()
        if item:
            return jsonify(item)
        return jsonify({'error': 'Pregunta no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_preguntas.route('/preguntasfrecuentes', methods=['POST'])
def crear_pregunta():
    conn = None
    cursor = None
    try:
        data = request.get_json() or {}
        pregunta = data.get('pregunta')
        respuesta = data.get('respuesta')
        orden = data.get('orden', 1)
        fecha_creacion = data.get('fecha_creacion')
        fecha_actualizacion = data.get('fecha_actualizacion')
        if not all([pregunta, respuesta, fecha_creacion, fecha_actualizacion]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400
        conn = get_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO Pregunta_Frecuente
            (pregunta, respuesta, orden, fecha_creacion, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(sql, (pregunta, respuesta, orden, fecha_creacion, fecha_actualizacion))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_preguntas.route('/preguntasfrecuentes/<int:id>', methods=['PUT'])
def actualizar_pregunta(id):
    conn = None
    cursor = None
    try:
        data = request.get_json() or {}
        pregunta = data.get('pregunta')
        respuesta = data.get('respuesta')
        orden = data.get('orden')
        fecha_creacion = data.get('fecha_creacion')
        fecha_actualizacion = data.get('fecha_actualizacion')
        campos = []
        valores = []
        for campo, valor in [
            ('pregunta', pregunta),
            ('respuesta', respuesta),
            ('orden', orden),
            ('fecha_creacion', fecha_creacion),
            ('fecha_actualizacion', fecha_actualizacion)
        ]:
            if valor is not None:
                campos.append(f"{campo} = %s")
                valores.append(valor)
        if not campos:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        valores.append(id)
        sql = f"UPDATE Pregunta_Frecuente SET {', '.join(campos)} WHERE ID = %s"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, valores)
        conn.commit()
        return jsonify({'mensaje': 'Pregunta actualizada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@bp_preguntas.route('/preguntasfrecuentes/<int:id>', methods=['DELETE'])
def eliminar_pregunta(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Pregunta_Frecuente WHERE ID = %s", (id,))
        conn.commit()
        return jsonify({'mensaje': 'Pregunta eliminada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()