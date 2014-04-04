from hcpxnat.interface import HcpInterface

cdb = HcpInterface(config='/home/NRG/mhilem01/.hcpxnat_cdb.cfg')

def get_matches(firstname, lastname):
    """ Check for firstname/lastname match on ConnectomeDB
    Takes multiple matches and possible matches into account
    """

    users = cdb.getUsers()
    matches, possible_matches = []

    for user in users:
        if lastname == user.get('lastname').lower() and \
           firstname == user.get('firstname').lower():
            matches.append(user)

    if not matches:
        for user in users:
            if lastname == user.get('lastname').lower() and \
               firstname[0] == user.get('fistname').lower()[0]:
               possible_matches.append(user)

    return matches, possible_matches

def check_membership():
    """ Check AD for 'Phase2OpenUsers' group membership
    """
    pass

def add_membership():
    """ Add to 'Phase2ControlledUsers'
    """
    pass

def generate_email():
    pass

def add_wiki_notes():
    pass

def check_credentials(username, password):
   """ From https://gist.github.com/ibeex/1288159
   Probably use code from http://www.grotan.com/ldap/python-ldap-samples.html
   Verifies credentials for username and password.
   Returns None on success or a string describing the error on failure
   """
   LDAP_SERVER = 'ldap://xxx'
   # fully qualified AD user name
   LDAP_USERNAME = '%s@xxx.xx' % username
   # your password
   LDAP_PASSWORD = password
   base_dn = 'DC=xxx,DC=xxx'
   ldap_filter = 'userPrincipalName=%s@xxx.xx' % username
   attrs = ['memberOf']
   try:
       # build a client
       ldap_client = ldap.initialize(LDAP_SERVER)
       # perform a synchronous bind
       ldap_client.set_option(ldap.OPT_REFERRALS, 0)
       ldap_client.simple_bind_s(LDAP_USERNAME, LDAP_PASSWORD)
   except ldap.INVALID_CREDENTIALS:
       ldap_client.unbind()
       return 'Wrong username ili password'
   except ldap.SERVER_DOWN:
       return 'AD server not awailable'
   # all is well
   # get all user groups and store it in cerrypy session for future use
   cherrypy.session[username] = str(ldap_client.search_s(base_dn,
                   ldap.SCOPE_SUBTREE, ldap_filter, attrs)[0][1]['memberOf'])
   ldap_client.unbind()
   return None

if __name__ == '__main__':
    firstname = 'Malcolm'.lower()
    lastname = 'Tobias'.lower()
    matches, possible_matches = get_matches(firstname, lastname)

    if matches: print "Matches:"
    for match in matches:
        print match

    if possible_matches and not matches: print "Possible matches:"
    for match in possible_matches:
        print match
