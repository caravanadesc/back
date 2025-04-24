# db.py
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

# 1) Carga variables de entorno
load_dotenv()

# 2) Configura parámetros para el pool
pool = pooling.MySQLConnectionPool(
    pool_name        = os.getenv('DB_POOL_NAME', 'mypool'),
    pool_size        = int(os.getenv('DB_POOL_SIZE', 5)),
    host             = os.getenv('DB_HOST', '69.62.71.171'),
    port             = int(os.getenv('DB_PORT', 3306)),
    user             = os.getenv('DB_USER', 'root'),
    password         = os.getenv('DB_PASSWORD', 'caravanadestrucs'),
    database         = os.getenv('DB_NAME', 'lab-ux'),
    pool_reset_session = True
)

def get_connection():
    """
    Devuelve una conexión del pool.
    Recuerda cerrar la conexión (conn.close()) para devolverla al pool.
    """
    return pool.get_connection()
