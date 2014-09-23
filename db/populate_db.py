from app.model import get_db
from app.hcprestricted import ad_bind, has_group_membership, config
from app.hcpxnat.interface import HcpInterface

""" Move to the root directory (same level as app/) to execute
"""

db = get_db()
ldap = ad_bind()
cdb = HcpInterface(url=config.get('hcpxnat', 'site'),
                   username=config.get('hcpxnat', 'username'),
                   password=config.get('hcpxnat', 'password'))

users = cdb.getUsers()
for u in users:
    if has_group_membership(u['login'], 'Phase2ControlledUsers'):
        print u['login'], "has restricted access."
        db.execute(
            "insert into restrictedaccess (firstname, lastname, email, login, status) \
            values ('%s', '%s', '%s', '%s', 'Access Granted')" % \
            (u['firstname'], u['lastname'], u['email'], u['login'])
            )
        db.commit()
db.close()

