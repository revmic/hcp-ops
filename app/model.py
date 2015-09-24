import sqlite3
import pymysql
import ConfigParser

from app import app
from app.views import g

config = ConfigParser.ConfigParser()
config.read('/Users/michael/.hcprestricted')


''' MODEL Methods '''


def connect_db():
    rv = sqlite3.connect(config.get('db', 'location'))
    # rv = sqlite3.connect('/Users/michael/Development/hcp_restricted/db/restricted.db')
    rv.row_factory = sqlite3.Row
    return rv


def connect_mysql():
    cnx = pymysql.connect(host=config.get('mysql', 'host'),
                          user=config.get('mysql', 'user'),
                          passwd=config.get('mysql', 'passwd'),
                          db=config.get('mysql', 'db'))
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


def get_mysql():
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = connect_mysql()
    return g.mysql_db


@app.teardown_appcontext
def close_db(error):
    # print error
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
    if hasattr(g, 'mysql_db'):
        g.mysql_db.close()
