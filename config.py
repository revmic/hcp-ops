from __future__ import print_function
import os
import socket
import ConfigParser

if 'hcp-ops' in socket.gethostname():
    ENV = 'prod'
else:
    ENV = 'dev'

#log = open("/tmp/debug.log", "w")

basedir = os.path.abspath(os.path.dirname(__file__))
config = ConfigParser.ConfigParser()
config_path = os.path.join(os.path.expanduser("~"), '.hcprestricted')
print(config_path)
#config_path = '/root/.hcprestricted'
#config_path = '/home/apache/.hcprestricted'
#config_path = os.path.join(os.sep, 'var', 'www', '.hcprestricted')
config.read(config_path)

CSRF_ENABLED = True
SECRET_KEY = config.get('db', 'secret_key')
DEBUG = True
JSON_SORT_KEY = False

BASIC_AUTH_USERNAME = config.get('site', 'username')
BASIC_AUTH_PASSWORD = config.get('site', 'password')
BASIC_AUTH_REALM = 'Restricted Access'

#log.write(str(config.sections()))

CC_LIST = ['scurtiss@brainvis.wustl.edu', 'rlriney@wustl.edu', 'hodgem@wustl.edu', 'akaushal@wustl.edu','plenzini@wustl.edu']
# CC_LIST = ['mhilema@gmail.com']

# This is the string used in SQL query to determine project from filename
PROJECTS = ['HCP', 'MGH']

# Sync Relay Monitor hostnames
RELAY_HOSTNAMES = ['wu-relay1', 'UMINN-relay1', 'harvard-relay1', 'MGH-relay1', 'UCLA-relay1', 'BMC-relay1']

#log.close()
