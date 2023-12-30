import os
from flask_login import login_required, LoginManager, login_user, logout_user, current_user, UserMixin
from db.database import obtener_conexion
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from db.forms import AgregarClienteForm, AgregarPlanForm, ActualizarPlanForm, LoginForm, RegistroClienteForm, AgregarAdminForm
from db.controlador import obtener_lista_clientes, agregar_cliente_db, buscar_cliente_por_id, actualizar_cliente_db, inactivar_cliente_db, obtener_lista_clientes_inactivos, reactivar_cliente_db, agregar_plan_db, obtener_planes_desde_db, obtener_plan_por_id, actualizar_plan_en_db, eliminar_plan_en_db, crear_membresia, obtener_membresias_cliente, obtener_todas_membresias, buscar_cliente_por_criterio, obtener_ultimos_clientes, obtener_nombres_y_precios_planes, obtener_id_cliente_por_usuario, eliminar_cliente_db, registrar_cliente, verificar_membresias_vencidas, buscar_cliente_por_id_con_membresias, editar_membresia, agregar_administrador_db, obtener_roles_del_usuario, rol_requerido, actualizar_estado_cliente, calcular_estado_membresia
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from db.models import db, Usuario, Membresia, Cliente
from datetime import datetime, date




app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/dorians_gym'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id):
    print(f"load_user - user_id: {user_id}")
    user = Usuario.query.get(int(user_id))
    print(f"Loaded user: {user}")
    if user:
        user.is_authenticated = True
        user.roles = obtener_roles_del_usuario(user)  
    return user



@app.route('/login', methods=['GET', 'POST'])
def login():
    #verificar_membresias_vencidas()
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = Usuario.query.filter_by(username=username, password=password).first()
        print(f"Type of user: {type(user)}")
        if user:
            login_user(user)  
            flash('Inicio de sesión exitoso', 'success')            
            if user.role == 'admin':
                return redirect(url_for('pagina_principal'))
            else:
                id_cliente = obtener_id_cliente_por_usuario(user.id_usuario)
                return redirect(url_for('datos_cliente', id_cliente=id_cliente))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))


@app.route('/datos_usuario')
@rol_requerido('admin')
def datos_usuario():
    
    if 'user_id' not in session:
        flash('Inicia sesión para ver tus datos.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    usuario = Usuario.query.get(user_id)

    if usuario:
        return render_template('datos_usuario.html', usuario=usuario)
    else:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('pagina_principal'))


@app.route('/registro', methods=['GET', 'POST'])
def registro_cliente():
    form = RegistroClienteForm()

    if form.validate_on_submit():
        cedula = form.cedula.data
        nombre = form.nombre.data
        apellido = form.apellido.data
        correo = form.correo.data
        telefono = form.telefono.data
        fecha_nacimiento = form.fecha_nacimiento.data          
        password = form.password.data        
        username = correo
        registrar_cliente(cedula, nombre, apellido, correo, telefono, fecha_nacimiento, username, password)
        return redirect(url_for('login'))

    return render_template('registro_cliente.html', form=form)



@app.route('/agregar_admin', methods=['GET', 'POST'])
@rol_requerido('admin')
def agregar_admin():
    
    if 'admin' not in obtener_roles_del_usuario(current_user):
    
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('pagina_principal'))

    form = AgregarAdminForm()
    if form.validate_on_submit():        
        username = form.username.data
        password = form.password.data        
        agregar_administrador_db(username, password)
        flash('Administrador registrado exitosamente', 'success')
        return redirect(url_for('pagina_principal'))
    return render_template('agregar_admin.html', form=form)





app.config['UPLOAD_FOLDER'] = 'static/uploads'



@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/pagina_principal')
@rol_requerido('admin')
def pagina_principal():
    if 'admin' in obtener_roles_del_usuario(current_user):
        return render_template('pagina_principal.html')
    else:
        return render_template('acceso_restringido.html')



@app.route('/crear_membresia', methods=['POST'])
@rol_requerido('admin')
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


@app.route('/editar_membresia/<int:id_membresia>', methods=['GET', 'POST'])
@rol_requerido('admin')
def editar_membresia_route(id_membresia):
    
    if request.method == 'POST':
        nueva_fecha_final = request.form.get('nueva_fecha_final')
        membresia = Membresia.obtener_membresia_por_id(id_membresia)
        id_cliente = membresia.id_cliente if membresia else None
        editar_membresia(id_membresia, nueva_fecha_final)
        
        if id_cliente is not None:
            actualizar_estado_cliente(id_cliente)
        
        flash('Fecha de membresía editada correctamente', 'success')
        return redirect(url_for('membresias_proximas_a_caducar')) 
    
    membresia = Membresia.obtener_membresia_por_id(id_membresia)
    id_cliente = membresia.id_cliente if membresia else None
    cliente = buscar_cliente_por_id(id_cliente)
        
    id_planes = [membresia.id_plan]    
    nombres_y_precios_planes = obtener_nombres_y_precios_planes(id_planes)
    
    return render_template('editar_membresia.html', membresia=membresia, nombres_y_precios_planes=nombres_y_precios_planes, cliente=cliente)





@app.route('/asignar_membresia/<int:id_cliente>', methods=['GET', 'POST'])
@rol_requerido('admin')
def asignar_membresia(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)

    if request.method == 'POST':
        id_plan = request.form.get('id_plan')
        fecha_inicio = request.form.get('fecha_inicio')
        crear_membresia(id_cliente, id_plan, fecha_inicio)
        flash('Membresía asignada correctamente', 'success')
        return redirect(url_for('membresias_cliente', id_cliente=id_cliente))

    planes = obtener_planes_desde_db()
    return render_template('asignar_membresia.html', cliente=cliente, planes=planes)


@app.route('/membresias_cliente/<int:id_cliente>')
@login_required
def membresias_cliente(id_cliente):
    cliente = buscar_cliente_por_id(id_cliente)
    
    if not current_user.tiene_rol('admin') and current_user.id_cliente != id_cliente:
        flash('Acceso no permitido', 'danger')
        return render_template('acceso_restringido.html'), 403

    membresias = obtener_membresias_cliente(id_cliente)
    
    id_planes = [membresia.id_plan for membresia in membresias]
    nombres_y_precios_planes = obtener_nombres_y_precios_planes(id_planes)

    return render_template('membresias_cliente.html', cliente=cliente, membresias=membresias, nombres_y_precios_planes=nombres_y_precios_planes)


@app.route('/membresias_activas_cliente/<int:id_cliente>')
@login_required
def membresias_activas_cliente(id_cliente):
    
    if current_user.role == 'admin':        
        cliente = Cliente.obtener_cliente_por_id(id_cliente)
        membresias_activas = cliente.obtener_membresias_activas()
        return render_template('membresias_activas_cliente.html', membresias_activas=membresias_activas, cliente=cliente)    
    
    elif current_user.role == 'cliente' and current_user.id_cliente == id_cliente:        
        cliente = Cliente.obtener_cliente_por_id(id_cliente)
        membresias_activas = cliente.obtener_membresias_activas()
        return render_template('membresias_activas_cliente.html', membresias_activas=membresias_activas, cliente=cliente)
    
    
    flash('No tienes permisos para ver las membresías activas de este cliente', 'warning')
    return redirect(url_for('index'))




@app.route('/todas_membresias')
@rol_requerido('admin')
def todas_membresias():
    membresias = obtener_todas_membresias()

    if not membresias:
        flash('No se encontraron membresías', 'warning')
        return redirect(url_for('index'))
    
    membresias_extendidas = []
    current_time = datetime.utcnow()

    id_planes = [membresia.id_plan for membresia in membresias]    
    nombres_precios_planes = obtener_nombres_y_precios_planes(id_planes)

    for membresia in membresias:
        cliente = buscar_cliente_por_id(membresia.id_cliente)
        nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}" if cliente else "Cliente no encontrado"
        
        vigente = membresia.fecha_final >= current_time.date()
        
        membresias_extendidas.append({
            'id_membresia': membresia.id_membresia,
            'fecha_inicio': membresia.fecha_inicio,
            'fecha_final': membresia.fecha_final,
            'id_cliente': membresia.id_cliente,
            'nombre_cliente': nombre_cliente,
            'id_plan': membresia.id_plan,
            'nombre_plan': nombres_precios_planes.get(membresia.id_plan, {}).get('nombre_plan', "Plan no encontrado"),
            'precio_plan': nombres_precios_planes.get(membresia.id_plan, {}).get('precio', "Precio no encontrado"),
             'vigente': vigente
        })

    return render_template('todas_membresias.html', membresias=membresias_extendidas, current_time=current_time)


@app.route('/membresias_proximas_a_caducar')
@rol_requerido('admin')
def membresias_proximas_a_caducar():    
    membresias = Membresia.obtener_membresias_proximas_a_caducar()
    
    if not membresias:
        flash('No se encontraron membresías próximas a caducar', 'warning')
        return redirect(url_for('gestion_membresias'))    
    
    for membresia in membresias:        
        membresia.vigente = calcular_estado_membresia(membresia) 
    
    return render_template('membresias_proximas_a_caducar.html', membresias=membresias)


@app.route('/membresias_caducadas')
@rol_requerido('admin')
def membresias_caducadas():
    membresias = Membresia.obtener_membresias_caducadas()
    if not membresias:
        flash('No se encontraron membresías caducadas', 'warning')
        return redirect(url_for('gestion_membresias'))
    return render_template('membresias_caducadas.html', membresias=membresias)


@app.route('/agregar_plan', methods=['GET', 'POST'])
@rol_requerido('admin')
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
@rol_requerido('admin')
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
@rol_requerido('admin')
def eliminar_plan(id_plan):
    eliminar_plan_en_db(id_plan)
    return redirect(url_for('planes_lista'))



@app.route('/planes_lista')
@rol_requerido('admin')
def planes_lista():
    planes = obtener_planes_desde_db()
    return render_template('planes_lista.html', planes=planes)


@app.route('/gestion_membresias', methods=['GET', 'POST'])
@rol_requerido('admin')
def gestion_membresias():
    resultados = []

    if request.method == 'POST':
        criterio = request.form.get('criterio')
        resultados = buscar_cliente_por_criterio(criterio)

    
    if not resultados:
        resultados = obtener_ultimos_clientes()

    return render_template('gestion_membresias.html', resultados=resultados)



@app.route('/lista_clientes')
@rol_requerido('admin')
def lista_clientes():
    search_term = request.args.get('search', '')
    clientes = obtener_lista_clientes(search_term)
    return render_template('lista_clientes.html', clientes=clientes)


def allowed_file(filename):
    # Esta función comprueba si la extensión del archivo es válida
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/lista_clientes_inactivos')
@rol_requerido('admin')
def lista_clientes_inactivos():
    clientes_inactivos = obtener_lista_clientes_inactivos()
    return render_template('lista_clientes_inactivos.html', clientes_inactivos=clientes_inactivos)


@app.route('/reactivar_cliente/<int:id_cliente>')
@rol_requerido('admin')
def reactivar_cliente(id_cliente):
    
    reactivar_cliente_db(id_cliente)
    
    return redirect(url_for('lista_clientes_inactivos'))


@app.route('/datos_cliente/<int:id_cliente>')
@login_required

def datos_cliente(id_cliente):
    cliente = buscar_cliente_por_id_con_membresias(id_cliente)
    if cliente:        
        if current_user.role == 'cliente' and current_user.id_cliente == id_cliente:        
            membresias_activas = Membresia.obtener_membresias_activas_cliente(id_cliente)
            return render_template('datos_cliente.html', cliente=cliente, membresias_activas=membresias_activas  )
        elif current_user.role == 'admin':
            membresias_activas = Membresia.obtener_membresias_activas_cliente(id_cliente)            
            return render_template('datos_cliente.html', cliente=cliente, membresias_activas=membresias_activas)
        else:
            flash('Acceso no autorizado.', 'danger')
            return redirect(url_for('datos_cliente', id_cliente=current_user.id_cliente))
    else:
        flash('Cliente no encontrado.', 'danger')        
        return redirect(url_for('lista_clientes'))



@app.route('/agregar_cliente', methods=['GET', 'POST'])
@rol_requerido('admin')
def agregar_cliente():
    form = AgregarClienteForm()

    if request.method == 'POST' and form.validate_on_submit():
        cedula = form.cedula.data
        nombre = form.nombre.data
        apellido = form.apellido.data
        correo = form.correo.data
        telefono = form.telefono.data
        fecha_nacimiento = form.fecha_nacimiento.data

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
        
        agregar_cliente_db(cedula, nombre, apellido, correo, telefono, fecha_nacimiento, filename)

        return redirect(url_for('lista_clientes'))

    return render_template('agregar_cliente.html', form=form)




@app.route('/actualizar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
@rol_requerido('admin')
def actualizar_cliente(id_cliente):
    form = AgregarClienteForm()

    
    cliente = buscar_cliente_por_id(id_cliente)

    if cliente is None:
        flash("Cliente no encontrado.", "error")
        return redirect(url_for('lista_clientes'))

    if request.method == 'POST' and form.validate_on_submit():
        
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

        
        actualizar_cliente_db(
            id_cliente,
            form.cedula.data,
            form.nombre.data,
            form.apellido.data,
            form.correo.data,
            form.telefono.data,
            form.fecha_nacimiento.data,  
            filename
        )

        return redirect(url_for('lista_clientes'))

    # Llenar el formulario con los datos actuales del cliente
    form.cedula.data = cliente.get('cedula', '')
    form.nombre.data = cliente.get('nombre', '')
    form.apellido.data = cliente.get('apellido', '')
    form.correo.data = cliente.get('correo', '')
    form.telefono.data = cliente.get('telefono', '')
    
    fecha_nacimiento = cliente.get('fecha_nacimiento')
    if fecha_nacimiento is not None:
        form.fecha_nacimiento.data = fecha_nacimiento

    return render_template('actualizar_cliente.html', form=form)



@app.route('/eliminar_cliente/<int:id_cliente>')
@rol_requerido('admin')
def eliminar_cliente(id_cliente):
    eliminar_cliente_db(id_cliente)
    return redirect(url_for('lista_clientes'))



@app.route('/inactivar_cliente/<int:id_cliente>')
@rol_requerido('admin')
def inactivar_cliente(id_cliente):
    # Llamada a la función para inactivar el cliente en la base de datos
    inactivar_cliente_db(id_cliente)
    # Redireccionar a la lista de clientes después de inactivar
    return redirect(url_for('lista_clientes'))

 
@app.route('/cumpleanios_proximos')
@rol_requerido('admin')
def cumpleanios_proximos():
    try:
        clientes_cumpleanios = Cliente.obtener_cumpleanios_proximos()
        return render_template('cumpleanios_proximos.html', clientes_cumpleanios=clientes_cumpleanios)
    except Exception as e:
        print(f"Error en la ruta /cumpleanios_proximos: {e}")
        return "Error interno del servidor", 500


if __name__ == '__main__':
    app.run(debug=True)
