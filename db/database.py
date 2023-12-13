import pymysql

# Función para obtener la conexión a la base de datos
def obtener_conexion():
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="",
            db="dorians_gym"  
        )
        return conn
    except pymysql.Error as error:
        print(f"Error al conectarse a la base de datos: {error}")
        return None
