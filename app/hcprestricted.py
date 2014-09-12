from hcpxnat.interface import HcpInterface
from email.mime.text import MIMEText
from datetime import date
from model import connect_db
from config import CC_LIST  # Move to config file
import ConfigParser
import smtplib
import ldap

config = ConfigParser.ConfigParser()
config.read('/Users/michael/.hcprestricted')

#cdb = HcpInterface(config='/home/NRG/mhilem01/.hcpxnat_cdb.cfg')
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
    #TODO - password and settings in config file
    ldap_uri=config.get('ldap', 'uri')
    bind_dn="cn=HCPDB Read Write,ou=Service Accounts,ou=HCP Users,dc=hcp,dc=mir"
    ldap_pass=config.get('ldap', 'password')
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    try:
        l = ldap.initialize(ldap_uri)
    except ldap.LDAPError,e:
        print e

    l.protocol_version = ldap.VERSION3
    l.set_option(ldap.OPT_REFERRALS, 0)

    try:
        l.bind_s(bind_dn,ldap_pass)
    except ldap.LDAPError, e:
        print e
    else:
        #print 'Sucessfully bound to AD'
        return l


def has_open_access(username):
    """ Check AD for 'Phase2OpenUsers' group membership
    """
    l = ad_bind()
    base_dn = "dc=hcp,dc=mir"
    filter='(name=%s)' % username
    retrieve_attrs = None
    scope = ldap.SCOPE_SUBTREE

    try:  # Search for username
        myResults = l.search_s(base_dn, scope, filter, retrieve_attrs)
    except ldap.LDAPError, e:
        print e
        return e

    # print myResults[0][1]['memberOf']

    access = False
    print myResults[0][1]
    try:
        for group in myResults[0][1]['memberOf']:
            if 'Phase2OpenUsers' in group:
                #print "Open access DUT accepted"
                access = True
    except TypeError, e:
        print e

    l.unbind()
    return access


def has_restricted_access(username):
    """ Check AD for 'Phase2OpenUsers' group membership
    """
    l = ad_bind()
    base_dn = "dc=hcp,dc=mir"
    filter='(name=%s)' % username
    retrieve_attrs = None
    scope = ldap.SCOPE_SUBTREE

    try:  # Search for username
        myResults = l.search_s(base_dn, scope, filter, retrieve_attrs)
    except ldap.LDAPError, e:
        print e
        return e

    access = False
    # print myResults
    # for r in myResults:
    #     print r

    try:
        for group in myResults[0][1]['memberOf']:
            if 'Phase2ControlledUsers' in group:
                #print "Has restricted access"
                access = True
    except TypeError, e:
        print 'TypeError: "%s" for %s' % (e, username)
    except KeyError, e:
        print 'KeyError: "%s" for %s' % (e, username)

    return access


def grant_restricted_access(username):
    """ Add to 'Phase2ControlledUsers'
    """
    l = ad_bind()
    #base_dn="dc=hcp,dc=mir"
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
    l.unbind()
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
    db = connect_db()

    # Check that the user is in Phase2ControlledUsers AD group
    # This should only happen in the case where access is granted
    # if not has_restricted_access(s['username']):
    #     s['status'] = 'Error'

    today = date.today()

    # Check if this is an existing record and update instead of insert
    result = db.execute(
        "SELECT id FROM restrictedaccess WHERE login='%s' AND email='%s'" % \
        (s['username'], s['email'])
        ).fetchone()

    try:
        existing_id = result[0]
    except TypeError:
        existing_id = None
    print "Existing ID:", existing_id

    if existing_id:
        q = "UPDATE restrictedaccess SET login='%s',email='%s',status='%s',status_updated='%s' WHERE id=%s" % \
            (s['username'], s['email'], s['status'], today, existing_id)
        print q
        db.execute(q)
    else:
        db.execute(
            "INSERT INTO restrictedaccess (firstname, lastname, email, login, status, status_updated) \
            VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % \
            (s['firstname'], s['lastname'], s['email'], s['username'], s['status'], today)
            )

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
    #has_open_access('hilemtest6')
    #has_restricted_access('hilemtest6')
    #grant_restricted_access('mhileman')
    #has_restricted_access('hilemtest6')

    firstname = 'Michael'.lower()
    lastname = 'Hileman'.lower()
    matches, possible_matches = search_cdb(firstname, lastname)

    # if matches: print "Matches:"
    # for match in matches:
    #     print match

    # if possible_matches and not matches: print "Possible matches:"
    # for match in possible_matches:
    #     print match
