import os
from db.database import obtener_conexion
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from db.forms import LoginForm, AgregarClienteForm, AgregarPlanForm, ActualizarPlanForm
from db.controlador import autenticar_usuario, obtener_lista_clientes, agregar_cliente_db, buscar_cliente_por_id, actualizar_cliente_db, inactivar_cliente_db, obtener_lista_clientes_inactivos, reactivar_cliente_db, agregar_plan_db, obtener_planes_desde_db, obtener_plan_por_id, actualizar_plan_en_db, eliminar_plan_en_db, crear_membresia, obtener_membresias_cliente, obtener_todas_membresias, buscar_cliente_por_criterio, obtener_nombre_plan, obtener_ultimos_clientes
from flask import jsonify


app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'

app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if autenticar_usuario(username, password):
            session['usuario_autenticado'] = True
            session['username'] = username
            return redirect(url_for('pagina_principal'))

        error_message = 'Credenciales no válidas. Inténtalo de nuevo.'
        return render_template('login.html', error_message=error_message)
    return render_template('login.html', form=form)

# Redirigir la ruta raíz '/' al login
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/pagina_principal')
def pagina_principal():
    return render_template('pagina_principal.html')


@app.route('/crear_membresia', methods=['POST'])
def crear_membresia_route():
    data = request.get_json()

    id_cliente = data.get('id_cliente')
    id_plan = data.get('id_plan')

    if id_cliente is None or id_plan is None:
        return jsonify({'error': 'Se requieren id_cliente e id_plan'}), 400

    try:
        crear_membresia(id_cliente, id_plan)
        return jsonify({'mensaje': 'Membresía creada exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': f'Error al crear membresía: {str(e)}'}), 500


@app.route('/asignar_membresia/<int:id_cliente>', methods=['GET', 'POST'])
def asignar_membresia(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)

    if request.method == 'POST':
        id_plan = request.form.get('id_plan')
        crear_membresia(id_cliente, id_plan)
        flash('Membresía asignada correctamente', 'success')
        return redirect(url_for('membresias_cliente', id_cliente=id_cliente))

    planes = obtener_planes_desde_db()
    return render_template('asignar_membresia.html', cliente=cliente, planes=planes)


@app.route('/membresias_cliente/<int:id_cliente>')
def membresias_cliente(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)
    membresias = obtener_membresias_cliente(id_cliente)
    
    print('print en app.py membresias encontradas', membresias)

    if not membresias:
        flash('No se encontraron membresías para el cliente', 'warning')
        print('No se encontraron membresías para el cliente')
        return redirect(url_for('lista_clientes'))
    
    # Obtén una lista de id_plan desde todas las membresías
    id_planes = [membresia.id_plan for membresia in membresias]

    # Obtén el diccionario de nombres de los planes
    nombres_planes = obtener_nombre_plan(id_planes)
    print('print en app', nombres_planes)

    return render_template('membresias_cliente.html', cliente=cliente, membresias=membresias, nombres_planes=nombres_planes)


# En app.py
@app.route('/todas_membresias')
def todas_membresias():
    membresias = obtener_todas_membresias()

    if not membresias:
        flash('No se encontraron membresías', 'warning')
        return redirect(url_for('index'))
    
    membresias_extendidas = []

    for membresia in membresias:
        cliente = buscar_cliente_por_id(membresia.id_cliente)
        nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}" if cliente else "Cliente no encontrado"

        # Cambia membresia.id_plan a una lista con un solo elemento [membresia.id_plan]
        nombres_planes = obtener_nombre_plan([membresia.id_plan])

        # Añade la información extendida a la lista
        membresias_extendidas.append({
            'id_membresia': membresia.id_membresia,
            'fecha_inicio': membresia.fecha_inicio,
            'fecha_final': membresia.fecha_final,
            'id_cliente': membresia.id_cliente,
            'nombre_cliente': nombre_cliente,
            'id_plan': membresia.id_plan,
            'nombre_plan': nombres_planes.get(membresia.id_plan, "Plan no encontrado")
        })

    return render_template('todas_membresias.html', membresias=membresias_extendidas)



@app.route('/agregar_plan', methods=['GET', 'POST'])
def agregar_plan():
    form = AgregarPlanForm()

    if form.validate_on_submit():
        agregar_plan_db(
            form.nombre_plan.data,
            form.precio.data,
            form.descripcion.data,
            form.num_dias.data
        )
        flash('¡Plan agregado exitosamente!', 'success')
        return redirect(url_for('planes_lista'))

    return render_template('agregar_plan.html', form=form)


@app.route('/actualizar_plan/<int:id_plan>', methods=['GET', 'POST'])
def actualizar_plan(id_plan):
    # Obtener el plan desde la base de datos
    plan = obtener_plan_por_id(id_plan)
    
    # Verificar si el plan existe
    if not plan:
        flash('Plan no encontrado', 'danger')
        return redirect(url_for('planes_lista'))

    # Crear el formulario y establecer los valores del plan en los campos
    form = ActualizarPlanForm()

    # Verificar si el formulario se ha enviado y es válido
    if form.validate_on_submit():
        # Actualizar el plan en la base de datos
        actualizar_plan_en_db(id_plan, form.nombre_plan.data, form.precio.data, form.descripcion.data, form.num_dias.data)
        
        # Redireccionar a la lista de planes
        flash('Plan actualizado exitosamente', 'success')
        return redirect(url_for('planes_lista'))
    
    # Llenar el formulario con los datos actuales del plan
    form.nombre_plan.data = plan['nombre_plan']
    form.precio.data = plan['precio']
    form.descripcion.data = plan['descripcion']
    form.num_dias.data = plan['num_dias']

    return render_template('actualizar_plan.html', form=form, plan=plan)



@app.route('/eliminar_plan/<int:id_plan>')
def eliminar_plan(id_plan):
    eliminar_plan_en_db(id_plan)
    return redirect(url_for('planes_lista'))



@app.route('/planes_lista')
def planes_lista():
    planes = obtener_planes_desde_db()
    return render_template('planes_lista.html', planes=planes)

'''
@app.route('/buscar_clientes/<termino>')
def buscar_clientes(termino):
    clientes = buscar_clientes_por_termino(termino)
    return jsonify(clientes)
'''

@app.route('/gestion_membresias', methods=['GET', 'POST'])
def buscar_clientes_form():
    resultados = []

    if request.method == 'POST':
        criterio = request.form.get('criterio')
        resultados = buscar_cliente_por_criterio(criterio)

    
    if not resultados:
        resultados = obtener_ultimos_clientes()

    return render_template('gestion_membresias.html', resultados=resultados)



@app.route('/lista_clientes')
def lista_clientes():
    search_term = request.args.get('search', '')
    clientes = obtener_lista_clientes(search_term)
    return render_template('lista_clientes.html', clientes=clientes)


def allowed_file(filename):
    # Esta función comprueba si la extensión del archivo es válida
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/lista_clientes_inactivos')
def lista_clientes_inactivos():
    clientes_inactivos = obtener_lista_clientes_inactivos()
    return render_template('lista_clientes_inactivos.html', clientes_inactivos=clientes_inactivos)


@app.route('/reactivar_cliente/<int:id_cliente>')
def reactivar_cliente(id_cliente):
    
    reactivar_cliente_db(id_cliente)
    
    return redirect(url_for('lista_clientes_inactivos'))



@app.route('/datos_cliente/<int:id_cliente>')
def datos_cliente(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)  

    if cliente:
        print(f"Cliente encontrado: {cliente}")
        return render_template('datos_cliente.html', cliente=cliente)
    else:
        flash('Cliente no encontrado.', 'danger')
        print("Cliente no encontrado.")
        return redirect(url_for('lista_clientes'))




@app.route('/agregar_cliente', methods=['GET', 'POST'])
def agregar_cliente():
    form = AgregarClienteForm()

    if request.method == 'POST' and form.validate_on_submit():
        cedula = form.cedula.data
        nombre = form.nombre.data
        apellido = form.apellido.data
        correo = form.correo.data
        telefono = form.telefono.data

        # Manejo de la carga de archivos (foto de perfil)
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '' and allowed_file(foto.filename):
                filename = secure_filename(foto.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(filepath)
            else:
                filename = None
        else:
            filename = None

        # Llamada a la función para agregar el cliente en la base de datos
        agregar_cliente_db(cedula, nombre, apellido, correo, telefono, filename)

        return redirect(url_for('lista_clientes'))

    return render_template('agregar_cliente.html', form=form)


@app.route('/actualizar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
def actualizar_cliente(id_cliente):
    form = AgregarClienteForm()

    # Obtener los datos del cliente por su ID
    cliente = buscar_cliente_por_id(id_cliente)

    if cliente is None:
        flash("Cliente no encontrado.", "error")
        return redirect(url_for('lista_clientes'))

    if request.method == 'POST' and form.validate_on_submit():
        # Manejo de la carga de archivos (foto de perfil)
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '' and allowed_file(foto.filename):
                filename = secure_filename(foto.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(filepath)
            else:
                filename = None
        else:
            filename = None

        # Llamada a la función para actualizar el cliente en la base de datos
        actualizar_cliente_db(id_cliente, form.cedula.data, form.nombre.data, form.apellido.data, form.correo.data, form.telefono.data, filename)

        return redirect(url_for('lista_clientes'))

    # Llenar el formulario con los datos actuales del cliente
    form.cedula.data = cliente.get('cedula', '')
    form.nombre.data = cliente.get('nombre', '')
    form.apellido.data = cliente.get('apellido', '')
    form.correo.data = cliente.get('correo', '')
    form.telefono.data = cliente.get('telefono', '')

    return render_template('actualizar_cliente.html', form=form)


@app.route('/inactivar_cliente/<int:id_cliente>')
def inactivar_cliente(id_cliente):
    # Llamada a la función para inactivar el cliente en la base de datos
    inactivar_cliente_db(id_cliente)
    # Redireccionar a la lista de clientes después de inactivar
    return redirect(url_for('lista_clientes'))

 




if __name__ == '__main__':
    app.run(debug=True)
