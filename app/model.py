import os
import sqlite3
import pymysql
import ConfigParser

from flask.ext.login import UserMixin

from app import app, login_manager
from app.views import g

config = ConfigParser.ConfigParser()
config_path = os.path.join(os.path.expanduser("~"), '.hcprestricted')
#config_path = os.path.join(os.sep, 'var', 'www', '.hcprestricted')
config.read(config_path)


class User(UserMixin):
    id = config.get('site', 'username')
    password = config.get('site', 'password')

    database = (
        {'hcp': (config.get('site', 'username'), 
                 config.get('site', 'password'))})

    #db = [{'username': config.get('site', 'username'), 
    #      'password': config.get('site', 'password')}]

    def __init__(self, username, password):
        self.id = username
        self.password = password

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        #print "inside User.get_id()"
        try:
            return unicode(self.id)  # python 2
        except NameError:
            return str(self.id)  # python 3

    @classmethod
    def get(cls, id):
        #print "inside User.get()"
        return cls(config.get('site', 'username'), config.get('site', 'password'))

    def __repr__(self):
        return '<User username: %s, password: %s>' % (self.id, self.password)

''' DB Connection Methods '''


def connect_db():
    rv = sqlite3.connect(config.get('db', 'location'))
    rv.row_factory = sqlite3.Row
    return rv


def connect_cinab():
    cnx = pymysql.connect(host=config.get('mysql', 'host'),
                          user=config.get('mysql', 'user'),
                          passwd=config.get('mysql', 'passwd'),
                          db=config.get('mysql', 'db'),
                          charset="utf8")
    return cnx.cursor()


def connect_aspera_geo():
    cnx = pymysql.connect(host=config.get('aspera', 'host'),
                          user=config.get('aspera', 'user'),
                          passwd=config.get('aspera', 'passwd'),
                          db=config.get('aspera', 'geodb'),
                          port=int(config.get('aspera', 'port')),
                          charset="utf8")
    return cnx.cursor()


def connect_aspera_stats():
    cnx = pymysql.connect(host=config.get('aspera', 'host'),
                          user=config.get('aspera', 'user'),
                          passwd=config.get('aspera', 'passwd'),
                          db=config.get('aspera', 'statsdb'),
                          port=int(config.get('aspera', 'port')),
                          charset="utf8")
    return cnx.cursor()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('bin/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """
    Opens a new db connection if there is none yet for
    the current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def get_db_cinab():
    if not hasattr(g, 'cinab_db'):
        g.mysql_db = connect_cinab()
    return g.mysql_db


def get_db_aspera_geo():
    if not hasattr(g, 'aspera_db_geo'):
        g.aspera_db_geo = connect_aspera_geo()
    return g.aspera_db_geo


def get_db_aspera_stats():
    if not hasattr(g, 'aspera_db_stats'):
        g.aspera_db_stats = connect_aspera_stats()
    return g.aspera_db_stats


@app.teardown_appcontext
def close_db(error):
    # print error
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
    if hasattr(g, 'cinab_db'):
        g.cinab_db.close()
    if hasattr(g, 'aspera_db_geo'):
        g.aspera_db_geo.close()
    if hasattr(g, 'aspera_db_stats'):
        g.aspera_db_stats.close()
