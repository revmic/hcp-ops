from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from wtforms.validators import Required

class RestrictedAccessForm(Form):
    firstname = TextField('firstname', validators=[Required()])
    lastname = TextField('lastname', validators=[Required()])
    generate_email_as = SelectField('gen_email_as',
        choices=[('hilemanm@mir.wustl.edu', 'Michael Hileman'),
                 ('hodgem@mir.wustl.edu', 'Mike Hodge')])

class EmailForm(Form):
    email_to = TextField('to', validators=[Required(), validators.Email()])
    email_from = TextField('from', validators=[Required(), validators.Email()])
    email_cc = TextField('cc')
    email_subject = TextField('subject', default='Access to Restricted Data in ConnectomeDB')
    email_body = TextAreaField('body')
