import os
import socket
import ConfigParser

if 'hcp-ops' in socket.gethostname():
    ENV = 'prod'
else:
    ENV = 'dev'

basedir = os.path.abspath(os.path.dirname(__file__))
config = ConfigParser.ConfigParser()
config_path = os.path.join(os.path.expanduser("~"), '.hcprestricted')
config.read(config_path)

CSRF_ENABLED = True
SECRET_KEY = config.get('db', 'secret_key')
DEBUG = True

CC_LIST = ['scurtiss@brainvis.wustl.edu', 'hilemanm@mir.wustl.edu', 'hodgem@mir.wustl.edu']
# CC_LIST = ['mhilema@gmail.com']
# CC_LIST = []

# This is the string used in SQL query to determine project from filename
PROJECTS = ['HCP\_', 'MGH\_']

