

from flask import Blueprint, request, jsonify
from db import get_connection

bp = Blueprint('proyecto', __name__)

@bp.route('/proyectos', methods=['GET'])
def listar_proyectos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM proyecto")
    resultados = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(resultados)

@bp.route('/proyectos/<int:id>', methods=['GET'])
def obtener_proyecto(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM proyecto WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    if resultado:
        return jsonify(resultado)
    return jsonify({'error': 'Proyecto no encontrado'}), 404

@bp.route('/proyectos', methods=['POST'])
def crear_proyecto():
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        INSERT INTO proyecto
        (nombre, tipo_estudio, imagen, descripcion, fecha_inicio, fecha_fin, progreso, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    valores = (
        data.get('nombre'),
        data.get('tipo_estudio'),
        data.get('imagen'),
        data.get('descripcion'),
        data.get('fecha_inicio'),
        data.get('fecha_fin'),
        data.get('progreso', 0),
        data.get('estado', 'planificacion')
    )
    cursor.execute(sql, valores)
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({'id': new_id}), 201

@bp.route('/proyectos/<int:id>', methods=['PUT'])
def actualizar_proyecto(id):
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        UPDATE proyecto
        SET nombre=%s, tipo_estudio=%s, imagen=%s, descripcion=%s, fecha_inicio=%s,
            fecha_fin=%s, progreso=%s, estado=%s
        WHERE id=%s
    """
    valores = (
        data.get('nombre'),
        data.get('tipo_estudio'),
        data.get('imagen'),
        data.get('descripcion'),
        data.get('fecha_inicio'),
        data.get('fecha_fin'),
        data.get('progreso', 0),
        data.get('estado', 'planificacion'),
        id
    )
    cursor.execute(sql, valores)
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'mensaje': 'Proyecto actualizado'})

@bp.route('/proyectos/<int:id>', methods=['DELETE'])
def eliminar_proyecto(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proyecto WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'mensaje': 'Proyecto eliminado'})