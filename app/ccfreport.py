import requests
import os

host = 'https://intradb-shadow3.humanconnectome.org'
user = 'mhileman'
pswd = 'NOPASSWORD'
dest_dir = '/var/www/hcp-ops/app/static/download/'
file_name = 'ccf-report.csv'


def get_json(uri):
    r = requests.get(uri, auth=(user, pswd))
    return r.json()['ResultSet']['Result']

def generate_ccf_report():
    uri = host + '/data/projects'
    r = requests.get(uri, auth=(user, pswd))
    projects = r.json()['ResultSet']['Result']
    #print projects
    print "getting counts for", len(projects), "projects"
    ccf_projects = []

    for p in projects:
        if 'CCF_' in p['ID'] and 'discard' not in p['name'].lower():
            ccf_projects.append(p)

    #print "Subject/session count for {0} CCF projects:\n".format(
    #    len(ccf_projects))

    file_path = os.path.join(dest_dir, file_name)
    csv_header = "Project ID,Project Name,PI,Subjects,Sessions\n"
    with open(file_path, 'w') as f:
        f.write(csv_header)

    for p in ccf_projects:
        uri = host + '/data/projects/{0}/subjects?format=json'.format(p['ID'])
        subjects = get_json(uri)

        uri = host + '/data/projects/{0}/experiments?'.format(p['ID']) + \
            'format=json&xsiType=xnat:mrSessionData'
        sessions = get_json(uri)

        #print "{0} -- {1}".format(p['ID'], p['name'])
        #print "PI: {0} {1}".format(p['pi_firstname'], p['pi_lastname'])
        #print "Subjects: {0}".format(len(subjects))
        #print "Sessions: {0}\n".format(len(sessions))

        csv_line = "{0},{1},{2} {3},{4},{5}\n".format(
            p['ID'], p['name'], p['pi_firstname'], p['pi_lastname'],
            len(subjects), len(sessions)
        )
        with open(file_path, 'a') as f:
            f.write(csv_line)

if __name__ == '__main__':
    generate_ccf_report()
