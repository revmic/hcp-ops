from hcpxnat.interface import HcpInterface
from email.mime.text import MIMEText
from datetime import date
from model import get_db
from sqlite3 import OperationalError
from config import CC_LIST, ENV, config  # Move to config file
from app.views import g
import ConfigParser
import smtplib
import ldap
import os

# config = ConfigParser.ConfigParser()
# config.read(os.path.join(os.path.expanduser('~'), '.hcprestricted'))

cdb = HcpInterface(url=config.get('hcpxnat', 'site'),
                   username=config.get('hcpxnat', 'username'),
                   password=config.get('hcpxnat', 'password'))


def search_cdb(firstname=None, lastname=None):
    """ Check for firstname/lastname match on ConnectomeDB
    Takes multiple matches and possible matches into account
    """
    users = cdb.getUsers()
    matches = []
    possible_matches = []

    for user in users:
        if lastname.lower() == user.get('lastname').lower() and \
           firstname.lower() == user.get('firstname').lower():
            matches.append(user)

    if not matches:  # No exact matches found, look for partial
        for user in users:
            # Look for either firstname only
            if firstname and not lastname:
                if firstname.lower() in user.get('firstname').lower():
                    possible_matches.append(user)
            # Or lastname only
            elif lastname and not firstname:
                if lastname.lower() in user.get('lastname').lower():
                    possible_matches.append(user)
            # Look for exact lastname and first character of firstname
            elif lastname.lower() == user.get('lastname').lower() and \
               firstname.lower()[0] == user.get('firstname').lower()[0]:
                possible_matches.append(user)
            # Look for substring of first and last names
            #elif lastname.lower() in user.get('lastname').lower():# and \
            #    possible_matches.append(user)
    return matches, possible_matches


def ad_bind():
    ldap_uri = config.get('ldap', 'uri')
    bind_dn = "cn=HCPDB Read Write,ou=Service Accounts,ou=HCP Users,dc=hcp,dc=mir"
    ldap_pass = config.get('ldap', 'password')
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    try:
        l = ldap.initialize(ldap_uri)
    except ldap.LDAPError, e:
        print e
        return None

    l.protocol_version = ldap.VERSION3
    l.set_option(ldap.OPT_REFERRALS, 0)

    try:
        l.bind_s(bind_dn, ldap_pass)
    except ldap.LDAPError, e:
        print e
    else:
        #print 'Sucessfully bound to AD'
        return l


def get_ldap():
    if not hasattr(g, 'ldap_conn'):
        g.ldap_conn = ad_bind()
    return g.ldap_conn


def has_group_membership(username, ad_group):
    """ Check AD for group membership
    """
    # global l
    # if not l:
    #     l = ad_bind()
    l = get_ldap()
    base_dn = "dc=hcp,dc=mir"
    filter = '(name=%s)' % username
    retrieve_attrs = None
    scope = ldap.SCOPE_SUBTREE

    try:  # Search for username
        myResults = l.search_s(base_dn, scope, filter, retrieve_attrs)
    except ldap.LDAPError, e:
        print e
        return e
    # print myResults[0][1]['memberOf']
    access = False
    # print myResults[0][1]
    try:
        for group in myResults[0][1]['memberOf']:
            if ad_group in group:
                access = True
    except TypeError, e:
        print e, "for", username, ad_group
    except KeyError, e:
        print e, "for", username, ad_group

    # l.unbind()
    return access


def grant_restricted_access(username):
    """ Add to 'Phase2ControlledUsers'
    """
    # global l
    # if not l:
    #     l = ad_bind()
    l = get_ldap()
    # base_dn="dc=hcp,dc=mir"
    user_dn = 'CN=%s,OU=Members,OU=HCP Users,DC=hcp,DC=mir' % username
    group_dn = 'CN=Phase2ControlledUsers,OU=Web Security Groups,OU=HCP Users,DC=hcp,DC=mir'
    add_member = [(ldap.MOD_ADD, 'member', user_dn.encode('ascii','ignore'))]

    try:  # Add user to group
        print group_dn
        print add_member
        l.modify_s(group_dn, add_member)
    except ldap.LDAPError, e:
        print "Error adding user to group: %s" % e
        return e

    print "Added to Phase2ControlledUsers"
    # l.unbind()
    return True


def send_email(subject, recipients, sender, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['CC'] = ', '.join(CC_LIST)

    session = smtplib.SMTP('mail.nrg.wustl.edu')
    try:
        session.sendmail(sender, recipients+CC_LIST, msg.as_string())
    except smtplib.SMTPException, e:
        print e
        return e
    else:
        return 1
    finally:
        session.quit()


def update_db(s):
    db = get_db()
    today = date.today()

    # Check if this is an existing record and update instead of insert
    # Need to check if name and email is matching for cases where
    # the user didn't have a connectome account
    # This will update the first record, TODO - handle multiple results
    result = db.execute(
        "SELECT id FROM restrictedaccess WHERE lastname='%s' AND email='%s'" % \
        (s['lastname'], s['email'])
        ).fetchone()

    try:
        existing_id = result[0]
    except:
        existing_id = None

    if existing_id:
        q = "UPDATE restrictedaccess SET login='%s',email='%s',status='%s',status_updated='%s' WHERE id=%s" % \
            (s['username'], s['email'], s['status'], today, existing_id)
        print q
        db.execute(q)
    else:
        q = "INSERT INTO restrictedaccess (firstname, lastname, email, login, status, status_updated) \
            VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % \
            (s['firstname'], s['lastname'], s['email'], s['username'], s['status'], today)
        print q
        db.execute(q)
    try:
        db.commit()
    except OperationalError:
        print "OperationalError on sqlite3 database. Retrying commit ..."
        db.commit()

    db.close()


"""
>>> # Insert a date object into the database
>>> today = date.today()
>>> c.execute('''INSERT INTO example(created_at) VALUES(?)''', (today,))
>>> db.commit()
>>>
>>> # Retrieve the inserted object
>>> c.execute('''SELECT created_at FROM example''')
>>> row = c.fetchone()
>>> print('The date is {0} and the datatype is {1}'.format(row[0], type(row[0])))
    # The date is 2013-04-14 and the datatype is <class 'str'>
"""

if __name__ == '__main__':

    firstname = 'Michael'.lower()
    lastname = 'Hileman'.lower()
    m, pm = search_cdb(firstname, lastname)
    print m

    # if matches: print "Matches:"
    # for match in matches:
    #     print match

    # if possible_matches and not matches: print "Possible matches:"
    # for match in possible_matches:
    #     print match
