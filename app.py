import os
from db.database import obtener_conexion
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from db.forms import LoginForm, AgregarClienteForm, AgregarPlanForm, ActualizarPlanForm
from db.controlador import autenticar_usuario, obtener_lista_clientes, agregar_cliente_db, buscar_cliente_por_cedula, buscar_cliente_por_id, buscar_clientes_por_termino, obtener_cliente_por_nombre_apellido, actualizar_cliente_db, inactivar_cliente_db, obtener_lista_clientes_inactivos, reactivar_cliente_db, agregar_plan_db, obtener_planes_desde_db, obtener_plan_por_id, actualizar_plan_en_db, eliminar_plan_en_db
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


@app.route('/agregar_plan', methods=['GET', 'POST'])
def agregar_plan():
    form = AgregarPlanForm()

    if form.validate_on_submit():
        agregar_plan_db(
            form.nombre_plan.data,
            form.precio.data,
            form.descripcion.data
        )
        flash('¡Plan agregado exitosamente!', 'success')
        return redirect(url_for('planes_lista'))

    return render_template('agregar_plan.html', form=form)


from flask import flash

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
        actualizar_plan_en_db(id_plan, form.nombre_plan.data, form.precio.data, form.descripcion.data)
        
        # Redireccionar a la lista de planes
        flash('Plan actualizado exitosamente', 'success')
        return redirect(url_for('planes_lista'))
    
    # Llenar el formulario con los datos actuales del plan
    form.nombre_plan.data = plan['nombre_plan']
    form.precio.data = plan['precio']
    form.descripcion.data = plan['descripcion']

    return render_template('actualizar_plan.html', form=form, plan=plan)



@app.route('/eliminar_plan/<int:id_plan>')
def eliminar_plan(id_plan):
    # Eliminar el plan en la base de datos
    eliminar_plan_en_db(id_plan)

    # Redireccionar a la lista de planes
    return redirect(url_for('planes_lista'))



@app.route('/planes_lista')
def planes_lista():
    planes = obtener_planes_desde_db()
    return render_template('planes_lista.html', planes=planes)



@app.route('/lista_clientes')
def lista_clientes():
    clientes = obtener_lista_clientes()
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

 

@app.route('/buscar_clientes/<termino>')
def buscar_clientes(termino):
    clientes = buscar_clientes_por_termino(termino)
    return jsonify(clientes)



if __name__ == '__main__':
    app.run(debug=True)
