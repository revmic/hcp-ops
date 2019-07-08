import os
import sys
import site

site.addsitedir('/var/www/hcp-ops/venv/lib/python2.7/site-packages')

path = '/var/www/hcp-ops'
if path not in sys.path:
    sys.path.append(path)

activate_env = '/var/www/hcp-ops/venv/bin/activate_this.py'
execfile(activate_env, dict(__file__=activate_env))

from app import app as application
