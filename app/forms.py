from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, HiddenField
from wtforms.validators import Required

class RestrictedAccessForm(Form):
    firstname = TextField('firstname', validators=[Required()])
    lastname = TextField('lastname', validators=[Required()])
    email = TextAreaField()
