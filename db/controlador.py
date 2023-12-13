from flask import current_app
import pymysql
from db.database import obtener_conexion
import os
from flask import render_template, redirect, url_for, flash, session, abort
from functools import wraps
import base64




def autenticar_usuario(username, password):
    query = "SELECT * FROM usuario WHERE username = %s AND password = %s"

    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute(query, (username, password))
            result = cursor.fetchone()

        return result is not None

    except pymysql.Error as error:
        print(f"Error al autenticar usuario: {error}")
        return False

    finally:
        if conn:
            conn.close()


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



def asignar_membresia_cliente(cedula, id_membresia):
    try:
        print("Iniciando asignar_membresia_cliente")
        print(f"Asignando membresía a cliente con cédula {cedula} y ID de membresía {id_membresia}")

        # Obtén información del cliente antes de asignar membresía
        cliente_anterior = buscar_cliente_por_cedula(cedula)
        print(f"Información anterior del cliente: {cliente_anterior}")

        # Asignar la membresía al cliente
        cliente = buscar_cliente_por_cedula(cedula)
        membresia = obtener_info_membresias_disponibles(id_membresia)
        cliente.asignar_membresia(membresia)

        print(f"Membresía asignada a cliente con cédula {cedula}. ID de membresía: {id_membresia}")

        # Obtén información del cliente después de asignar membresía
        cliente_actualizado = buscar_cliente_por_cedula(cedula)
        print(f"Información actualizada del cliente: {cliente_actualizado}")

        flash('Membresía asignada con éxito', 'success')
    except Exception as e:
        print(f"Error al asignar membresía: {e}")
        flash('Error al asignar membresía', 'error')




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
                if cliente_dict['foto_nombre']:
                    cliente_dict['foto_url'] = url_for('static', filename=f'uploads/{cliente_dict["foto_nombre"]}')
                else:
                    cliente_dict['foto_url'] = None

            return cliente_dict
    except Exception as error:
        print(f"Error al buscar cliente por ID: {error}")
        return None



def obtener_info_membresias_disponibles():
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute("SELECT id_membresia, nom_membresia, duracion, costo FROM membresia")
            return [dict(zip(cursor.column_names, row)) for row in cursor.fetchall()]
    except Exception as error:
        print(f"Error al obtener información de membresías disponibles: {error}")
        return []


def obtener_membresias_disponibles():
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute("SELECT id_membresia, nom_membresia FROM membresia")
            return cursor.fetchall()
    except Exception as error:
        print(f"Error al obtener membresías disponibles: {error}")
        return []


def obtener_lista_clientes():
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cliente WHERE estado = 1")
            clientes = cursor.fetchall()
            print(clientes)
            return clientes
    except Exception as e:
        print(f"Error al obtener la lista de clientes: {e}")
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




# En tu función buscar_clientes_por_termino en controlador.py
def buscar_clientes_por_termino(termino):
    try:
        with obtener_conexion().cursor() as cursor:
            cursor.execute(
                "SELECT nombre, apellido, cedula, telefono FROM cliente WHERE nombre LIKE %s OR apellido LIKE %s LIMIT 10",
                (f"%{termino}%", f"%{termino}%")
            )
            clientes = cursor.fetchall()
            return [{'nombre': cliente[0], 'apellido': cliente[1], 'cedula': cliente[2], 'telefono': cliente[3]} for cliente in clientes]
    except Exception as error:
        print(f"Error al buscar clientes por término: {error}")
        return []


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





def requerir_rol(rol):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'usuario_autenticado' not in session or 'rol' not in session or session['rol'] != rol:
                abort(403)  # Prohibido
            return func(*args, **kwargs)
        return wrapper
    return decorador
