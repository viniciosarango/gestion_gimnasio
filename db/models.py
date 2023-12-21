import pymysql
from datetime import datetime, timedelta
from db.database import obtener_conexion

from flask_login import UserMixin
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy



db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    id_usuario = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'cliente'), nullable=False)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))

    def __repr__(self):
        return f"<Usuario {self.username}>"

class Membresia:
    def __init__(self, id_membresia, fecha_inicio, fecha_final, id_cliente, id_plan, precio_plan, nombre_cliente=None, nombre_plan=None):
        self.id_membresia = id_membresia
        self.fecha_inicio = fecha_inicio
        self.fecha_final = fecha_final
        self.id_cliente = id_cliente
        self.id_plan = id_plan
        self.precio_plan = precio_plan
        self.nombre_cliente = nombre_cliente
        self.nombre_plan = nombre_plan
    
    @staticmethod
    def crear_instancia_membresia(fila):
        return Membresia(
            id_membresia=fila[0],
            fecha_inicio=fila[1],
            fecha_final=fila[2],
            id_cliente=fila[3],
            id_plan=fila[4],
            precio_plan=fila[5],
            nombre_cliente=fila[6],
            nombre_plan=fila[7]
        )


    @classmethod
    def from_dict(cls, membresia_dict):
        if membresia_dict:
            return cls(
                id_membresia=membresia_dict.get('id_membresia'),
                fecha_inicio=membresia_dict.get('fecha_inicio'),
                fecha_final=membresia_dict.get('fecha_final'),
                id_cliente=membresia_dict.get('id_cliente'),
                id_plan=membresia_dict.get('id_plan')
            )
        return None
 
    @classmethod
    def obtener_membresias_cliente(cls, id_cliente):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT membresia.*, planes.precio
                    FROM membresia
                    JOIN planes ON membresia.id_plan = planes.id_plan
                    WHERE membresia.id_cliente = %s
                """, (id_cliente,))
                membresias_data = cursor.fetchall()
                membresias = [cls(*membresia) for membresia in membresias_data]
                return membresias
        except Exception as e:
            print(f"Error al obtener las membresías del cliente: {e}")
            return []
        finally:
            if conn:
                conn.close()


    @classmethod
    def obtener_todas_membresias(cls):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM membresia")
                membresias_data = cursor.fetchall()
                print('Resultados directos de la base de datos:', membresias_data)  # Agrega este print para verificar qué está devolviendo la base de datos
                membresias = [cls(*membresia, precio_plan=None) for membresia in membresias_data]
                print('print de @classmethod def obtener_todas_membresias', membresias)  # Agrega este print para verificar qué está devolviendo
                return membresias
        except Exception as e:
            print(f"Error al obtener todas las membresías: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @classmethod
    def obtener_membresias_proximas_a_caducar(cls, dias=7):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                fecha_actual = datetime.now().strftime("%Y-%m-%d")

                # Consulta para obtener membresías próximas a caducar con información del cliente y el plan
                cursor.execute("""
                    SELECT membresia.id_membresia, membresia.fecha_inicio, membresia.fecha_final, 
                        membresia.id_cliente, membresia.id_plan, planes.precio AS precio_plan,
                        cliente.nombre AS nombre_cliente, planes.nombre_plan AS nombre_plan
                    FROM membresia
                    JOIN planes ON membresia.id_plan = planes.id_plan
                    JOIN cliente ON membresia.id_cliente = cliente.id_cliente
                    WHERE fecha_final BETWEEN %s AND DATE_ADD(%s, INTERVAL %s DAY)
                """, (fecha_actual, fecha_actual, dias))

                membresias_data = cursor.fetchall()

                # Crear instancias de la clase Membresia utilizando la función auxiliar
                membresias = [cls.crear_instancia_membresia(fila) for fila in membresias_data]

                return membresias
        except Exception as e:
            print(f"Error al obtener las membresías próximas a caducar: {e}")
            return []
        finally:
            if conn:
                conn.close()
