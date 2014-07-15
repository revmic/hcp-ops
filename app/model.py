import sqlite3
from app import app
from app.views import g

''' MODEL Methods '''
def connect_db():
    # rv = sqlite3.connect(config.DATABASE)
    rv = sqlite3.connect('/Users/michael/Development/hcp_restricted_dev/db/restricted.db')
    rv.row_factory = sqlite3.Row
    return rv

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

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
