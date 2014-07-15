from app.model import connect_db
from app.hcprestricted import ad_bind, has_restricted_access, config
from app.hcpxnat.interface import HcpInterface

db = connect_db()
ldap = ad_bind()
cdb = HcpInterface(url=config.get('hcpxnat', 'site'),
                   username=config.get('hcpxnat', 'username'),
                   password=config.get('hcpxnat', 'password'))

users = cdb.getUsers()
for u in users:
    if has_restricted_access(u['login']):
        print u['login'], "has restricted access."
        db.execute(
            "insert into restrictedaccess (firstname, lastname, email, login, status) \
            values ('%s', '%s', '%s', '%s', 'Access Granted')" % \
            (u['firstname'], u['lastname'], u['email'], u['login'])
            )
        db.commit()
db.close()

