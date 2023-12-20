import pymysql
from datetime import datetime, timedelta
from db.database import obtener_conexion
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
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
    def __init__(self, id_membresia, fecha_inicio, fecha_final, id_cliente, id_plan, precio_plan):
        self.id_membresia = id_membresia
        self.fecha_inicio = fecha_inicio
        self.fecha_final = fecha_final
        self.id_cliente = id_cliente
        self.id_plan = id_plan
        self.precio_plan = precio_plan

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
    def obtener_membresia_por_id(cls, id_membresia):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM membresia
                    WHERE id_membresia = %s
                """, (id_membresia,))
                membresia_data = cursor.fetchone()
                if membresia_data:
                    membresia = cls(*membresia_data)
                    return membresia
                else:
                    return None
        except Exception as e:
            print(f"Error al obtener la membresía por ID: {e}")
            return None
        finally:
            if conn:
                conn.close()


