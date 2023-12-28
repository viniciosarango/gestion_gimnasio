import pymysql
from datetime import datetime, timedelta, date
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

    def get_id(self):
        return str(self.id_usuario)

    def is_authenticated(self):
        return True  #

    def is_active(self):
        return True  

    def is_anonymous(self):
        return False

    def check_password(self, password):
        # Implementa la verificación de contraseña
        return check_password_hash(self.password, password)
    
    def tiene_rol(self, rol):
        return self.role == rol




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
        nombre_plan = fila[7] if len(fila) > 7 else None
        nombre_cliente = fila.get('nombre_cliente') if 'nombre_cliente' in fila else None
        return Membresia(
            id_membresia=fila[0],
            fecha_inicio=fila[1],
            fecha_final=fila[2],
            id_cliente=fila[3],
            id_plan=fila[4],
            precio_plan=fila[5],
            #nombre_cliente=fila[6],
            #nombre_plan=fila[7] if len(fila) > 7 else None
            nombre_cliente=nombre_cliente,
            nombre_plan=nombre_plan
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
                    ORDER BY fecha_final DESC
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
    def obtener_membresias_activas_cliente(cls, id_cliente):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT membresia.*, planes.precio, planes.nombre_plan, cliente.nombre AS nombre_cliente, cliente.apellido
                    FROM membresia
                    JOIN planes ON membresia.id_plan = planes.id_plan
                    WHERE membresia.id_cliente = %s
                    AND membresia.fecha_final >= CURDATE()  
                    ORDER BY fecha_final DESC
                """, (id_cliente,))
                membresias_data = cursor.fetchall()                
                membresias = [cls.crear_instancia_membresia(fila) for fila in membresias_data]                
                for m in membresias:
                    print(f"ID: {m.id_membresia}, Nombre del Plan: {m.nombre_plan}") 
                return membresias
        
        except Exception as e:
            print(f"Error al obtener las membresías activas del cliente: {e}")
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
                
                cursor.execute("""
                    SELECT membresia.id_membresia, membresia.fecha_inicio, membresia.fecha_final, 
                        membresia.id_cliente, membresia.id_plan, planes.precio AS precio_plan,
                        CONCAT(cliente.nombre, ' ', cliente.apellido) AS nombre_cliente, planes.nombre_plan AS nombre_plan
                    FROM membresia
                    JOIN planes ON membresia.id_plan = planes.id_plan
                    JOIN cliente ON membresia.id_cliente = cliente.id_cliente
                    WHERE fecha_final BETWEEN %s AND DATE_ADD(%s, INTERVAL %s DAY)
                """, (fecha_actual, fecha_actual, dias))

                membresias_data = cursor.fetchall()                
                membresias = [cls.crear_instancia_membresia(fila) for fila in membresias_data]
                return membresias
        
        except Exception as e:
            print(f"Error al obtener las membresías próximas a caducar: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @classmethod
    def obtener_membresias_caducadas(cls):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                fecha_actual = datetime.now().strftime("%Y-%m-%d")

                # Consulta para obtener membresías caducadas con información del cliente y el plan
                cursor.execute("""
                    SELECT membresia.id_membresia, membresia.fecha_inicio, membresia.fecha_final, 
                        membresia.id_cliente, membresia.id_plan, planes.precio AS precio_plan,
                        CONCAT(cliente.nombre, ' ', cliente.apellido) AS nombre_cliente, 
                        planes.nombre_plan AS nombre_plan
                    FROM membresia
                    JOIN planes ON membresia.id_plan = planes.id_plan
                    JOIN cliente ON membresia.id_cliente = cliente.id_cliente
                    WHERE fecha_final < %s
                """, (fecha_actual,))


                membresias_data = cursor.fetchall()
                
                membresias = [cls.crear_instancia_membresia(fila) for fila in membresias_data]
                print("obterner membresias caducadas", membresias_data)

                return membresias
        except Exception as e:
            print(f"Error al obtener las membresías caducadas: {e}")
            return []
        finally:
            if conn:
                conn.close()


    @classmethod
    def obtener_membresia_por_id(cls, id_membresia):
        conn = obtener_conexion()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM membresia WHERE id_membresia = %s", (id_membresia,)
                )
                membresia_data = cursor.fetchone()

                print("Resultado de la consulta:", membresia_data)  # Nuevo print para ver el resultado de la consulta

                if membresia_data:
                    return cls(
                        id_membresia=membresia_data[0],
                        fecha_inicio=membresia_data[1],
                        fecha_final=membresia_data[2],
                        id_cliente=membresia_data[3],
                        id_plan=membresia_data[4],
                        precio_plan=membresia_data[5] if len(membresia_data) > 5 else None,
                    )
                else:
                    return None
        except pymysql.Error as error:
            print(f"Error al obtener membresía por ID: {error}")
        finally:
            conn.close()

    






class Cliente:
    def __init__(self, id_cliente, cedula, nombre, apellido, correo, telefono, estado, foto_nombre, fecha_nacimiento):
        self.id_cliente = id_cliente
        self.cedula = cedula
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.telefono = telefono
        self.estado = estado
        self.foto_nombre = foto_nombre
        self.fecha_nacimiento = fecha_nacimiento

    def calcular_edad(self):
        if self.fecha_nacimiento:
            fecha_nacimiento = datetime.strptime(str(self.fecha_nacimiento), "%Y-%m-%d").date()
            hoy = date.today()
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            return edad
        return None
    
    def obtener_membresias_activas(self):
        return Membresia.obtener_membresias_activas_cliente(self.id_cliente)

    def actualizar_estado(self, nuevo_estado):
        conn = obtener_conexion()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE cliente SET estado = %s WHERE id_cliente = %s",
                    (nuevo_estado, self.id_cliente)
                )
                conn.commit()
        except pymysql.Error as error:
            print(f"Error al actualizar el estado del cliente: {error}")
        finally:
            conn.close()

    @classmethod
    def obtener_cliente_por_id(cls, id_cliente):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM cliente WHERE id_cliente = %s", (id_cliente,))
                cliente_data = cursor.fetchone()
                if cliente_data:
                    # Crear una instancia de la clase Cliente utilizando los datos de la base de datos
                    cliente = cls(*cliente_data)
                    return cliente
                else:
                    print(f"No se encontró cliente con ID {id_cliente}.")
                    return None
        except Exception as e:
            print(f"Error al obtener cliente por ID: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    
    @classmethod
    def obtener_todos_los_clientes(cls):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM cliente")
                clientes_data = cursor.fetchall()

                if clientes_data:
                    # Crear instancias de la clase Cliente utilizando los datos de la base de datos
                    clientes = [cls(*fila) for fila in clientes_data]
                    return clientes
                else:
                    print("No se encontraron clientes.")
                    return []
        except Exception as e:
            print(f"Error al obtener todos los clientes: {e}")
            return []
        finally:
            if conn:
                conn.close()

    
    @classmethod
    def obtener_cumpleanios_proximos(cls, dias=7):
        try:
            conn = obtener_conexion()
            with conn.cursor() as cursor:
                hoy = date.today()
                fecha_limite = hoy + timedelta(days=dias)
                
                cursor.execute("""
                    SELECT *
                    FROM cliente
                    WHERE DAYOFYEAR(fecha_nacimiento) BETWEEN DAYOFYEAR(%s) AND DAYOFYEAR(%s)
                """, (hoy, fecha_limite))
                clientes_data = cursor.fetchall()
                if clientes_data:
                    
                    clientes = [cls(*fila) for fila in clientes_data]
                    
                    for cliente in clientes:
                        cliente.edad = cliente.calcular_edad()
                        
                    return clientes
                else:
                    print("No se encontraron clientes con cumpleaños próximos.")
                    return []
        except Exception as e:
            print(f"Error al obtener los cumpleaños próximos: {e}")
            return []
        finally:
            if conn:
                conn.close()



clientes = Cliente.obtener_cumpleanios_proximos()
for cliente in clientes:
    print(f"ID: {cliente.id_cliente}, Nombre: {cliente.nombre} {cliente.apellido}, Fecha de Nacimiento: {cliente.fecha_nacimiento}")