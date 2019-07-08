from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, SelectField, PasswordField, validators
from wtforms.validators import DataRequired

class LoginForm(Form):
    username = TextField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])

class RestrictedAccessForm(Form):
    firstname = TextField('firstname', validators=[DataRequired()])
    lastname = TextField('lastname', validators=[DataRequired()])
    username = TextField('username')
    email = TextField('email')
    generate_email_as = SelectField('gen_email_as',
        choices=[('mhileman@wustl.edu', 'Michael Hileman'),
                 ('hodgem@wustl.edu', 'Mike Hodge'),
                 ('akaushal@wustl.edu', 'Atul Kaushal'),
                 ('plenzini@wustl.edu', 'Petra Lenzini')])

class EmailForm(Form):
    email_to = TextField('to', validators=[DataRequired(), validators.Email()])
    email_from = TextField('from', validators=[DataRequired(), validators.Email()])
    email_cc = TextField('cc')
    email_subject = TextField('subject', default='Access to Restricted Data in ConnectomeDB')
    email_body = TextAreaField('body')
