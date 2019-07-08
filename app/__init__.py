from flask import Flask
from flask.ext.mail import Mail
#from flask.ext.basicauth import BasicAuth
from flask.ext.login import LoginManager
__author__ = 'michael'

app = Flask(__name__)
app.config.from_object('config')
mail = Mail(app)
#auth = BasicAuth(app)
login_manager = LoginManager()
login_manager.init_app(app)

from app import views
