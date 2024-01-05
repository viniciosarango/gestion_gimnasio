from flask_wtf import FlaskForm
from wtforms import StringField, DateField, FloatField, TextAreaField, PasswordField, SubmitField, FileField, SelectField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo
from wtforms import validators


class LoginForm(FlaskForm):
    username = StringField('Usuario', [validators.DataRequired()])
    password = PasswordField('Contraseña', [validators.DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class AgregarClienteForm(FlaskForm):
    cedula = StringField('Cédula', validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono')
    fecha_nacimiento = DateField('Fecha de Nacimiento', validators=[DataRequired()], format='%Y-%m-%d')
    foto = FileField('Foto de Perfil')
    nueva_contrasena = PasswordField('Nueva Contraseña')
    submit = SubmitField('Agregar/Actualizar Cliente')


class AgregarPlanForm(FlaskForm):
    nombre_plan = StringField('Nombre del Plan', validators=[DataRequired()])
    precio = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    descripcion = TextAreaField('Descripción')
    num_dias = IntegerField('Duración en días', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Agregar Plan')

class ActualizarPlanForm(FlaskForm):
    nombre_plan = StringField('Nombre del Plan', validators=[DataRequired()])
    precio = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    descripcion = TextAreaField('Descripción')
    num_dias = IntegerField('Duración en días', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Actualizar Plan')

class RegistroClienteForm(FlaskForm):    
    cedula = StringField('Cédula', validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    fecha_nacimiento = DateField('Fecha de Nacimiento', validators=[DataRequired()], format='%Y-%m-%d')
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Registrar cuenta')

class AgregarAdminForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired(), EqualTo('confirm_password', message='Las contraseñas deben coincidir')])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired()])
    submit = SubmitField('Registrar Administrador')