import os
import ConfigParser
## TODO: Move this all to .hcprestricted config file

basedir = os.path.abspath(os.path.dirname(__file__))
config = ConfigParser.ConfigParser()
config.read('/Users/michael/.hcprestricted')

CSRF_ENABLED = True
SECRET_KEY = 'Not so secret'

#CC_LIST = ['scurtiss@brainvis.wustl.edu', 'hilemanm@mir.wustl.edu', 'hodgem@mir.wustl.edu']
CC_LIST = ['mhilema@gmail.com']

''' DATABASE '''
# Load default config and override config from an environ var
DATABASE = config.get('db', 'location')
DEBUG = True
SECRET_KEY = config.get('db', 'secret_key')
USERNAME = config.get('db', 'username')
PASSWORD = config.get('db', 'password')
