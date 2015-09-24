from datetime import date

from model import get_db
from hcprestricted import has_group_membership, cdb
from app import app


def update_access_count(group):
    with app.app_context():
        db = get_db()
    users = cdb.getUsers()
    today = date.today()
    count = 0
    emails = []

    if group == 'ConnectomeUsers':
        q = "UPDATE access_stats SET count=%s,last_updated='%s' WHERE shortname='%s'" % \
            (len(users), today, group)
    else:
        for u in users:
            if has_group_membership(u['login'], group) and u['email'] not in emails:

                ####################################################################
                if group == 'Phase2OpenUsers':
                    print u['email']
                    # f.write(u['email'] + '\n')
                ####################################################################

                emails.append(u['email'])
                count += 1
        q = "UPDATE access_stats SET count=%s,last_updated='%s' WHERE shortname='%s'" % \
            (count, today, group)

    # db.execute(q)
    # db.commit()
    print q


def update_aspera_stats():
    print "Updating Aspera Stats"


if __name__ == '__main__':
    update_access_count('ConnectomeUsers')
    update_aspera_stats()
