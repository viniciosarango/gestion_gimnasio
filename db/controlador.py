from flask import current_app
import pymysql
from db.database import obtener_conexion
import os
from flask import render_template, redirect, url_for, flash, session, abort
from functools import wraps
import base64
from datetime import datetime
from datetime import timedelta
from db.models import Membresia, Usuario
from flask_login import login_required
from werkzeug.security import check_password_hash
import traceback




# Función para agregar cliente a la base de datos
def agregar_cliente_db(cedula, nombre, apellido, correo, telefono, foto_nombre):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cliente (cedula, nombre, apellido, correo, telefono, foto_nombre, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (cedula, nombre, apellido, correo, telefono, foto_nombre, 1)
        )

        conn.commit()
    except Exception as e:
        print(f"Error al agregar cliente a la base de datos: {e}")
    finally:
        if conn:
            conn.close()


# Función para actualizar los datos de un cliente en la base de datos (incluyendo la foto)
def actualizar_cliente_db(id_cliente, cedula, nombre, apellido, correo, telefono, foto_nombre):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cliente
            SET cedula = %s, nombre = %s, apellido = %s, correo = %s, telefono = %s, foto_nombre = %s
            WHERE id_cliente = %s
            """,
            (cedula, nombre, apellido, correo, telefono, foto_nombre, id_cliente)
        )

        conn.commit()
    except Exception as e:
        print(f"Error al actualizar cliente en la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Función para inactivar un cliente en la base de datos
def inactivar_cliente_db(id_cliente):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("UPDATE cliente SET estado = 0 WHERE id_cliente = %s", (id_cliente,))

        conn.commit()
    except Exception as e:
        print(f"Error al inactivar cliente en la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def obtener_duracion_plan_por_id(id_plan):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("SELECT num_dias FROM planes WHERE id_plan = %s", (id_plan,))
            duracion = cursor.fetchone()
            if duracion:
                return duracion[0]
    except pymysql.Error as error:
        print(f"Error al obtener la duración del plan desde la base de datos: {error}")
    finally:
        if conn:
            conn.close()
    return None


def obtener_nombres_y_precios_planes(id_planes):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id_plan, nombre_plan, precio
                FROM planes
                WHERE id_plan IN %s
            """, (tuple(id_planes),))
            planes_data = cursor.fetchall()
            planes_dict = {plan[0]: {'nombre': plan[1], 'precio': plan[2]} for plan in planes_data}
            return planes_dict
    except Exception as e:
        print(f"Error al obtener los nombres y precios de los planes: {e}")
        return {}
    finally:
        if conn:
            conn.close()



def crear_membresia(id_cliente, id_plan, fecha_inicio):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            
            # Duración en días del plan desde la base de datos
            duracion_en_dias = obtener_duracion_plan_por_id(id_plan)
            
            # Calcular fecha_final usando la función
            fecha_final = calcular_fecha_final(fecha_inicio, duracion_en_dias)

            # Insertar membresía en la base de datos
            cursor.execute(
                "INSERT INTO membresia (fecha_inicio, fecha_final, id_cliente, id_plan) VALUES (%s, %s, %s, %s)",
                (fecha_inicio, fecha_final, id_cliente, id_plan)
            )
            conn.commit()
    except pymysql.Error as error:
        print(f"Error al crear membresía: {error}")
    finally:
        conn.close()


def actualizar_membresia(id_membresia, nueva_fecha_inicio, nuevo_id_plan):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE membresia
                SET fecha_inicio = %s, id_plan = %s
                WHERE id_membresia = %s
            """, (nueva_fecha_inicio, nuevo_id_plan, id_membresia))
            conn.commit()
            nueva_fecha_inicio = datetime.strptime(nueva_fecha_inicio, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            print(f"Membresía {id_membresia} actualizada exitosamente.")
            
            return redirect(url_for('membresias_cliente', id_cliente=id_membresia))

    except pymysql.Error as error:
        print(f"Error al actualizar membresía: {error}")
    finally:
        if conn:
            conn.close()


def obtener_membresia_por_id(id_membresia):
    try:
        membresia = Membresia.obtener_membresia_por_id(id_membresia)

        if not membresia:
            flash('No se encontró la membresía', 'warning')
            return redirect(url_for('index'))

        planes = obtener_planes_desde_db()

        return render_template('editar_membresia.html', membresia=membresia, planes=planes)
    except Exception as e:
        print(f"Error al obtener la membresía por ID: {e}")
        raise  # Propaga la excepción para obtener más detalles en la consola


def calcular_fecha_final(fecha_inicio, duracion_en_dias):
    # Convertir fecha_inicio a datetime
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")

    # Calcular fecha_final
    fecha_final = fecha_inicio + timedelta(days=duracion_en_dias)
    
    return fecha_final


def obtener_todas_membresias():
    try:
        membresias = Membresia.obtener_todas_membresias()
        return membresias
    except Exception as e:
        print(f"Error al obtener todas las membresías: {e}")
        return []


def obtener_membresias_cliente(id_cliente):
    try:
        membresias = Membresia.obtener_membresias_cliente(id_cliente)
        return membresias
        
    except Exception as e:
        print(f"Error al obtener las membresías del cliente: {e}")
        return []


def buscar_cliente_por_criterio(criterio):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            # Realizar la búsqueda por nombre, apellido o cédula
            cursor.execute("""
                SELECT id_cliente, nombre, apellido, cedula
                FROM cliente
                WHERE nombre LIKE %s OR apellido LIKE %s OR cedula LIKE %s
            """, (f'%{criterio}%', f'%{criterio}%', f'%{criterio}%'))
            resultados = cursor.fetchall()

        return resultados
    except Exception as e:
        print(f"Error al buscar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()




def buscar_cliente_por_cedula(cedula):
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute("SELECT * FROM cliente WHERE cedula = %s", (cedula,))
            return cursor.fetchone()
    except Exception as error:
        print(f"Error al buscar cliente por cédula: {error}")
        return None



def buscar_cliente_por_id(id_cliente):
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute("SELECT * FROM cliente WHERE id_cliente = %s", (id_cliente,))
            cliente = cursor.fetchone()
            if cliente:
                # Obtener los nombres de las columnas
                column_names = [column[0] for column in cursor.description]
                
                cliente_dict = dict(zip(column_names, cliente))  # Convertir a diccionario
                
                cliente_dict['nombre_cliente'] = f"{cliente_dict['nombre']} {cliente_dict['apellido']}"

                if cliente_dict['foto_nombre']:
                    cliente_dict['foto_url'] = url_for('static', filename=f'uploads/{cliente_dict["foto_nombre"]}')
                else:
                    cliente_dict['foto_url'] = None

            return cliente_dict
    except Exception as error:
        print(f"Error al buscar cliente por ID: {error}")
        return None


def obtener_lista_clientes(search_term=None):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            if search_term:
                # Si hay un término de búsqueda, filtrar los resultados
                cursor.execute("SELECT * FROM cliente WHERE estado = 1 AND (cedula LIKE %s OR nombre LIKE %s OR apellido LIKE %s)",
                               (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                # Si no hay término de búsqueda, obtener todos los clientes activos
                cursor.execute("SELECT * FROM cliente WHERE estado = 1")

            clientes = cursor.fetchall()
            return clientes
    except Exception as e:
        print(f"Error al obtener la lista de clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()


# En controlador.py
def obtener_ultimos_clientes():
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cliente ORDER BY id_cliente DESC LIMIT 5")
            clientes = cursor.fetchall()
            return clientes
    except Exception as e:
        print(f"Error al obtener los últimos clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()



# Función para obtener la lista de clientes inactivos
def obtener_lista_clientes_inactivos():
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cliente WHERE estado = 0")
        clientes_inactivos = cursor.fetchall()
        return clientes_inactivos
    except Exception as e:
        print(f"Error al obtener lista de clientes inactivos: {e}")
    finally:
        if conn:
            conn.close()

# Función para reactivar un cliente en la base de datos
def reactivar_cliente_db(id_cliente):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("UPDATE cliente SET estado = 1 WHERE id_cliente = %s", (id_cliente,))

        conn.commit()
    except Exception as e:
        print(f"Error al reactivar cliente en la base de datos: {e}")
    finally:
        if conn:
            conn.close()




def obtener_cliente_por_nombre_apellido(nombre, apellido):
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute(
                "SELECT id_cliente, nombre, apellido FROM cliente WHERE nombre = %s AND apellido = %s LIMIT 1",
                (nombre, apellido)
            )
            cliente = cursor.fetchone()
            if cliente:
                return {'id': cliente[0], 'nombre': cliente[1], 'apellido': cliente[2]}
    except Exception as error:
        print(f"Error al obtener cliente por nombre y apellido: {error}")
    return None

# Función para agregar plan a la base de datos
def agregar_plan_db(nombre, precio, descripcion, num_dias):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO planes (nombre_plan, precio, descripcion, num_dias)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, precio, descripcion, num_dias)
        )

        conn.commit()
    except Exception as e:
        print(f"Error al agregar plan a la base de datos: {e}")
    finally:
        if conn:
            conn.close()



def obtener_plan_por_id(id_plan):
    plan = None
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("SELECT id_plan, nombre_plan, precio, descripcion, num_dias FROM planes WHERE id_plan = %s", (id_plan,))
        plan_data = cursor.fetchone()

        if plan_data:
            # Crear un objeto con atributos
            plan = {
                'id_plan': plan_data[0],
                'nombre_plan': plan_data[1],
                'precio': plan_data[2],
                'descripcion': plan_data[3],
                'num_dias': plan_data[4]
            }

    except Exception as e:
        print(f"Error al obtener el plan desde la base de datos: {e}")
    finally:
        if conn:
            conn.close()

    return plan



def actualizar_plan_en_db(id_plan, nombre_plan, precio, descripcion, num_dias):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE planes
            SET nombre_plan = %s, precio = %s, descripcion = %s, num_dias = %s
            WHERE id_plan = %s
            """,
            (nombre_plan, precio, descripcion, num_dias, id_plan )
        )

        conn.commit()
    except Exception as e:
        print(f"Error al actualizar el plan en la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def eliminar_plan_en_db(id_plan):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM planes WHERE id_plan = %s", (id_plan,))
        
        conn.commit()
        flash('Plan eliminado exitosamente', 'success')
    except Exception as e:
        print(f"Error al eliminar plan de la base de datos: {e}")
        flash('Error al eliminar plan', 'danger')
    finally:
        if conn:
            conn.close()


def obtener_planes_desde_db():
    planes = []
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("SELECT id_plan, nombre_plan, precio, descripcion, num_dias FROM planes")
        planes = cursor.fetchall()
        

    except Exception as e:
        print(f"Error al obtener planes desde la base de datos: {e}")
    finally:
        if conn:
            conn.close()

    return planes

'''
def requerir_rol(rol):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'usuario_autenticado' not in session or 'rol' not in session or session['rol'] != rol:
                abort(403)  # Prohibido
            return func(*args, **kwargs)
        return wrapper
    return decorador
'''