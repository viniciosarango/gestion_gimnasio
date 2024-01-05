from flask import current_app

import pymysql
from db.database import obtener_conexion
import os
from flask import render_template, redirect, url_for, flash, session, abort
from functools import wraps
import base64
from datetime import datetime, time
from datetime import timedelta

from .models import db, Membresia, Usuario, Cliente

from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import traceback
import random
import string
from functools import wraps
from sqlalchemy.exc import IntegrityError




def agregar_administrador_db(username, password):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usuario (username, password, role)
            VALUES (%s, %s, %s)
            """,
            (username, password, 'admin')  
        )

        conn.commit()

    except Exception as e:
        print(f"Error al agregar administrador a la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def rol_requerido(rol_minimo):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if current_user.is_authenticated:
                if not current_user.tiene_rol(rol_minimo):
                    flash("No tienes permisos para acceder a esta página.", "danger")
                    return redirect(url_for('index'))
                return func(*args, **kwargs)
            else:
                flash("Debes iniciar sesión para acceder a esta página.", "danger")
                return redirect(url_for('login'))
        return decorated_view
    return wrapper



def obtener_roles_del_usuario(user):
    if user:
        return [user.role]
    return []


def validar_cedula(cedula):
    if len(cedula) != 10 or not cedula.isdigit():
        flash("Cédula inválida. Debe ser un número de 10 dígitos.", "error")
        return False
    total = 0
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]    
    for i in range(9):
        resultado = int(cedula[i]) * coeficientes[i]
        total += resultado if resultado < 10 else resultado - 9    
    digito_verificador = 10 - (total % 10)
    digito_verificador = 0 if digito_verificador == 10 else digito_verificador    
    resultado = digito_verificador == int(cedula[9])
    #flash(f"Validación para cédula {cedula}: {resultado}", "success" if resultado else "error")
    return resultado



def cedula_unica(cedula):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM cliente WHERE cedula = %s", (cedula,))
            cliente_existente = cursor.fetchone()
            print(f"Valor de cliente_existente: {cliente_existente}")
            return cliente_existente is None
    except Exception as e:
        print(f"Error al verificar unicidad de cédula: {e}")
        return False
    finally:
        if conn:
            conn.close()



def agregar_cliente_db(cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre):
    if not validar_cedula(cedula):
        flash("Cédula inválida. Debe ser un número de 10 dígitos.", "error")
        return

    if not cedula_unica(cedula):
        flash("Error: La cédula ya está registrada en el sistema.", "error")
        return
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
                
        cursor.execute("SELECT id_cliente FROM cliente WHERE cedula = %s", (cedula,))
        id_cliente_existente = cursor.fetchone()
        if id_cliente_existente:
            flash("Error: La cédula ya está registrada en el sistema", "error")
            return
        
        cursor.execute(
            """
            INSERT INTO cliente (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, 0)  
        )

        conn.commit()
        
        cursor.execute("SELECT LAST_INSERT_ID()")
        id_cliente = cursor.fetchone()[0]
        
        cursor.execute(
            """
            INSERT INTO usuario (username, password, role, id_cliente)
            VALUES (%s, %s, %s, %s)
            """,
            (correo, cedula, 'cliente', id_cliente)
        )

        conn.commit()
        flash("Cliente registrado exitosamente", "success")

    except IntegrityError:        
        flash("Error: La cédula ya está registrada en el sistema.", "error")
    
    except Exception as e:
        print(f"Error al agregar cliente en la base de datos: {e}")
        flash("Error al procesar la solicitud.", "error")
    
    finally:
        if conn:
            conn.close()


def registrar_cliente(cedula, nombre, apellido, correo, telefono, fecha_nacimiento, username, password):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        if not validar_cedula(cedula):
            flash("Cédula inválida. Debe ser un número de 10 dígitos.", "error")
            return False
        
        if not cedula_unica(cedula):
            flash("Error: La cédula ya está registrada en el sistema.", "error")
            return False

        # Insertar cliente en la tabla Cliente
        cursor.execute(
            """
            INSERT INTO cliente (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, 0)  # Estado inactivo al inicio
        )

        conn.commit()

        # Obtener el id_cliente del cliente recién insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        id_cliente = cursor.fetchone()[0]

        # Insertar usuario en la tabla Usuario asociado al cliente
        cursor.execute(
            """
            INSERT INTO usuario (username, password, role, id_cliente)
            VALUES (%s, %s, %s, %s)
            """,
            (username, password, 'cliente', id_cliente)
        )

        conn.commit()
        flash("Cliente registrado exitosamente", "success")

    except Exception as e:
        print(f"Error al agregar cliente a la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def actualizar_cliente_db(id_cliente, cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, nueva_contrasena=None):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cliente
            SET cedula = %s, nombre = %s, apellido = %s, correo = %s, telefono = %s, fecha_nacimiento = %s, foto_nombre = %s
            WHERE id_cliente = %s
            """,
            (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, id_cliente)
        )
        
         
        if nueva_contrasena is not None:            
            cursor.execute(
                """
                UPDATE usuario
                SET username = %s, password = %s
                WHERE id_cliente = %s
                """,
                (correo, nueva_contrasena, id_cliente)
            )
        else:            
            cursor.execute(
                """
                UPDATE usuario
                SET username = %s
                WHERE id_cliente = %s
                """,
                (correo, id_cliente)
            )

        conn.commit()
    except Exception as e:
        print(f"Error al actualizar cliente en la base de datos: {e}")
    finally:
        if conn:
            conn.close()



def actualizar_perfil_db(id_cliente, cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, nueva_contrasena=None):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        # Actualiza los campos del cliente
        cursor.execute(
            """
            UPDATE cliente
            SET cedula = %s, nombre = %s, apellido = %s, correo = %s, telefono = %s, fecha_nacimiento = %s, foto_nombre = %s
            WHERE id_cliente = %s
            """,
            (cedula, nombre, apellido, correo, telefono, fecha_nacimiento, foto_nombre, id_cliente)
        )
        
        if nueva_contrasena is not None:
            print(f"Debug: Nueva contraseña: {nueva_contrasena}")

            cursor.execute(
                """
                UPDATE usuario
                SET username = %s, password = %s
                WHERE id_cliente = %s
                """,
                (correo, nueva_contrasena, id_cliente)
            )
        elif correo != obtener_correo_por_id_cliente(id_cliente):            
            cursor.execute(
                """
                UPDATE usuario
                SET username = %s
                WHERE id_cliente = %s
                """,
                (correo, id_cliente)
            )

        conn.commit()
    except Exception as e:
        print(f"Error al actualizar el perfil del cliente en la base de datos: {e}")
    finally:
        if conn:
            conn.close()



def obtener_correo_por_id_cliente(id_cliente):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT username
            FROM usuario
            WHERE id_cliente = %s
            """,
            (id_cliente,)
        )

        correo = cursor.fetchone()

        return correo[0] if correo else None
    except Exception as e:
        print(f"Error al obtener el correo por id_cliente: {e}")
    finally:
        if conn:
            conn.close()


def eliminar_cliente_db(id_cliente):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        # Eliminar las membresías asociadas al cliente
        cursor.execute(
            """
            DELETE FROM membresia
            WHERE id_cliente = %s
            """,
            (id_cliente,)
        )

        # Eliminar al usuario asociado al cliente
        cursor.execute(
            """
            DELETE FROM usuario
            WHERE id_cliente = %s
            """,
            (id_cliente,)
        )

        # Eliminar al cliente
        cursor.execute(
            """
            DELETE FROM cliente
            WHERE id_cliente = %s
            """,
            (id_cliente,)
        )

        conn.commit()
        flash('Cliente eliminado exitosamente.', 'success')

    except Exception as e:
        print(f"Error al eliminar cliente de la base de datos: {e}")
        flash('Error al eliminar cliente.', 'danger')

    finally:
        if conn:
            conn.close()








def obtener_id_cliente_por_usuario(user_id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()        
        cursor.execute(
            """
            SELECT id_cliente FROM usuario
            WHERE id_usuario = %s
            """,
            (user_id,)
        )

        id_cliente = cursor.fetchone()

        if id_cliente:
            return id_cliente[0]
        else:
            print(f"No se encontró el id_cliente para el user_id {user_id}")
            return None

    except Exception as e:
        print(f"Error al obtener id_cliente por usuario: {e}")
        return None
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


def calcular_fecha_final(fecha_inicio, duracion_en_dias): 
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fecha_final = fecha_inicio + timedelta(days=duracion_en_dias)
    return fecha_final


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
            planes_dict = {plan[0]: {'nombre_plan': plan[1], 'precio': plan[2]} for plan in planes_data}
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
            duracion_en_dias = obtener_duracion_plan_por_id(id_plan)
            fecha_final = calcular_fecha_final(fecha_inicio, duracion_en_dias)
            fecha_actual = datetime.combine(datetime.now().date(), time())

            cursor.execute(
                "INSERT INTO membresia (fecha_inicio, fecha_final, id_cliente, id_plan) VALUES (%s, %s, %s, %s)",
                (fecha_inicio, fecha_final, id_cliente, id_plan)
            )            
            conn.commit()

            print(f"Fecha actual: {fecha_actual}")
            print(f"Fecha final: {fecha_final}")
            
            cursor.execute(
                "UPDATE cliente SET estado = 1 WHERE id_cliente = %s",
                (id_cliente,)
            )
            conn.commit()

            #actualizar_estado_cliente(id_cliente)

    except pymysql.Error as error:
        print(f"Error al crear membresía: {error}")
    finally:
        conn.close()


def actualizar_estado_cliente(id_cliente):
    cliente = Cliente.obtener_cliente_por_id(id_cliente)
    if cliente:
        membresias_activas = cliente.obtener_membresias_activas()
        estado = 1 if membresias_activas else 0
        cliente.actualizar_estado(estado)




def editar_membresia(id_membresia, nueva_fecha_final):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE membresia SET fecha_final = %s WHERE id_membresia = %s",
                (nueva_fecha_final, id_membresia)
            )
            conn.commit()            
            cursor.execute("SELECT id_cliente FROM membresia WHERE id_membresia = %s", (id_membresia,))
            id_cliente = cursor.fetchone()[0]

            membresias_activas = Membresia.obtener_membresias_activas_cliente(id_cliente)

            if not membresias_activas:
                actualizar_estado_cliente(id_cliente)
    except pymysql.Error as error:
        print(f"Error al editar membresía: {error}")
    finally:
        conn.close()

from datetime import datetime

def calcular_estado_membresia(membresia):
    fecha_actual = datetime.utcnow().date()
    return membresia.fecha_final >= fecha_actual




def gestionar_vencimiento_membresias():
    membresias_caducadas = Membresia.obtener_membresias_caducadas()

    for membresia in membresias_caducadas:
        actualizar_estado_cliente(membresia.id_cliente, 0)


def verificar_membresias_vencidas():    
    membresias_caducadas = Membresia.obtener_membresias_caducadas()
    print("Membresías caducadas:", membresias_caducadas)

    for membresia in membresias_caducadas:
        actualizar_estado_cliente(membresia.id_cliente, 0)



def obtener_todas_membresias():
    try:
        membresias = Membresia.obtener_todas_membresias()
        print("Todas las Membresías:", membresias)

        return membresias
    except Exception as e:
        print(f"Error al obtener todas las membresías: {e}")
        return []


def obtener_membresias_cliente(id_cliente):
    try:
        membresias = Membresia.obtener_membresias_cliente(id_cliente)
        print("Membresías Obtenidas:", membresias)

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
                cliente_dict['fecha_nacimiento'] = cliente_dict.get('fecha_nacimiento', 'Fecha no disponible')

                if cliente_dict['foto_nombre']:
                    cliente_dict['foto_url'] = url_for('static', filename=f'uploads/{cliente_dict["foto_nombre"]}')
                else:
                    cliente_dict['foto_url'] = None

            return cliente_dict
    except Exception as error:
        print(f"Error al buscar cliente por ID: {error}")
        return None

def buscar_cliente_por_id_con_membresias(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)
    if cliente:
        cliente['membresias'] = Membresia.obtener_membresias_cliente(id_cliente)
    return cliente


def obtener_lista_clientes(search_term=None):
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            if search_term:
                # Si hay un término de búsqueda, filtrar los resultados
                cursor.execute("SELECT * FROM cliente WHERE (cedula LIKE %s OR nombre LIKE %s OR apellido LIKE %s) ORDER BY id_cliente ASC",
                               (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                # Si no hay término de búsqueda, obtener todos los clientes activos
                cursor.execute("SELECT * FROM cliente ORDER BY id_cliente DESC")

            clientes = cursor.fetchall()
            return clientes
    except Exception as e:
        print(f"Error al obtener la lista de clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()


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

