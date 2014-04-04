from flask.ext.wtf import Form
from wtforms import TextField
from wtforms.validators import Required

class SearchConnectomeForm(Form):
    firstname = TextField('firstname', validators = [Required()])
    lastname = TextField('lastname', validators = [Required()])
