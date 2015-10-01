import os
import sqlite3
import pymysql
import ConfigParser

from app import app
from app.views import g

config = ConfigParser.ConfigParser()
config_path = os.path.join(os.path.expanduser("~"), '.hcprestricted')
config.read(config_path)


''' MODEL Methods '''


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
                          charset="utf8")
    return cnx.cursor()


def connect_aspera_stats():
    cnx = pymysql.connect(host=config.get('aspera', 'host'),
                          user=config.get('aspera', 'user'),
                          passwd=config.get('aspera', 'passwd'),
                          db=config.get('aspera', 'statsdb'),
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
