from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class AgregarClienteForm(FlaskForm):
    cedula = StringField('Cédula', validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono')
    foto = FileField('Foto de Perfil')
    submit = SubmitField('Agregar/Actualizar Cliente')



