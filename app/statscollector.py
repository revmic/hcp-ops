from datetime import date, datetime
from collections import OrderedDict
from iso3166 import countries
import json

from model import *
from hcprestricted import has_group_membership, cdb
from config import basedir
from app import app

# TODO - last_updated json
app.config["JSON_SORT_KEY"] = False


def collect_connectomedb_stats():
    print "\n", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), \
        "-- Updating DUT Stats"
    # AD group names that we want updated
    group_map = {
        'HCP': ['Phase2OpenUsers', 'Phase2ControlledUsers'],
        'MGH': ['MGH_HCPUsers']
    }
    ldap_name_map = {
        'Phase2OpenUsers': 'Open Access',
        'Phase2ControlledUsers': 'Restricted Access',
        'MGH_HCPUsers': 'Open Access'
    }

    stats = {}

    users = cdb.getUsers()
    stats['ConnectomeDB'] = [{'users': len(users)}]

    with app.app_context():
        for project, groups in group_map.iteritems():
            stats[project] = []

            for group in groups:
                print "-- Updating count for", group
                count = 0
                emails = []

                for u in users:
                    # Count if the user has AD group membership
                    # and hasn't already been counted
                    if has_group_membership(u['login'], group) \
                            and u['email'] not in emails:
                        emails.append(u['email'])
                        count += 1

                group_stat = {ldap_name_map[group]: count}
                stats[project].append(group_stat)

    print stats

    with open(os.path.join(basedir, 'db', 'dut.json'), 'w') as outfile:
        json.dump(stats, outfile)


def collect_aspera_stats():
    print "\n", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), \
        "-- Updating Aspera Download History"

    with app.app_context():

        aspera_db = get_db_aspera_stats()

        # Downloads to date - Month, Year, Size, Files, Users
        queries = [
            ("All", "SELECT YEAR(s.started_at) AS Year, MONTH(s.started_at) AS Month, SUM(f.bytes_written) AS Bytes, COUNT(DISTINCT(s.cookie)) AS Users, COUNT(f.status) AS Files FROM fasp_sessions AS s INNER JOIN fasp_files AS f ON s.session_id=f.session_id WHERE f.status='completed' AND f.file_basename NOT LIKE '%.md5' GROUP BY YEAR(s.started_at), MONTH(s.started_at)"),
            ("HCP", "SELECT YEAR(s.started_at) AS Year, MONTH(s.started_at) AS Month, SUM(f.bytes_written) AS Bytes, COUNT(DISTINCT(s.cookie)) AS Users, COUNT(f.status) AS Files FROM fasp_sessions AS s INNER JOIN fasp_files AS f ON s.session_id=f.session_id WHERE f.status='completed' AND (f.file_fullpath LIKE '%HCP\_%' OR f.file_fullpath LIKE '%LS\_%' OR f.file_fullpath REGEXP 'live/[0-9][0-9][0-9][0-9][0-9][0-9]') AND f.file_basename NOT LIKE '%.md5' GROUP BY YEAR(s.started_at), MONTH(s.started_at)"),
            ("MGH", "SELECT YEAR(s.started_at) AS Year, MONTH(s.started_at) AS Month, SUM(f.bytes_written) AS Bytes, COUNT(DISTINCT(s.cookie)) AS Users, COUNT(f.status) AS Files FROM fasp_sessions AS s INNER JOIN fasp_files AS f ON s.session_id=f.session_id WHERE f.status='completed' AND (f.file_fullpath LIKE '%MGH\_%') AND f.file_basename NOT LIKE '%.md5'")
        ]

        results = []

        for query in queries:
            print query
            proj = query[0]
            q = query[1]

            aspera_db.execute(q)

            bytes_ = []
            files = []
            users = []
            months = []

            for row in aspera_db:
                month = "%s-%s" % (row[0], row[1])
                months.append(month)
                bytes_.append(int(row[2]))
                users.append(row[3])
                files.append(row[4])

            # Derived data
            terabytes = []
            files_thousands = []

            for i in bytes_:
                terabytes.append(float(i)/(1024*1024*1024*1024))
            for i in files:
                files_thousands.append(i/1000)

            data = OrderedDict([
                ('project', proj),
                ('total_bytes', sum(bytes_)),
                ('total_files', sum(files)),
                ('total_users', sum(users)),
                ('bytes', bytes_),
                ('terabytes', terabytes),
                ('files', files),
                ('files_thousands', files_thousands),
                ('users', users),
                ('months', months)
            ])
            # data = {
            #     'project': proj,
            #     'total_bytes': sum(bytes_),
            #     'total_files': sum(files),
            #     'total_users': sum(users),
            #     'bytes': bytes_,
            #     'terabytes': terabytes,
            #     'files': files,
            #     'files_thousands': files_thousands,
            #     'users': users,
            #     'months': months
            # }
            results.append(data)

        json_object = {
            'results': results,
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(os.path.join(basedir, 'db', 'aspera.json'), 'w') as outfile:
            json.dump(json_object, outfile, sort_keys=False)


def collect_geolocation():
    """
    Aggregate Aspera and CinaB geolocation data from respective sources.
    """
    print "\n", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), \
        "-- Updating Geolocation Data"

    # aspera_downloads = {'United States': 3, 'Canada': 1}
    aspera_downloads = get_aspera_geo()

    # cinab_orders = {'Australia': 1, 'Canada': 2}
    cinab_orders = get_cinab_geo()

    combine_geolocation(cinab_orders, aspera_downloads)


def get_aspera_geo():
    """
    Requires the geolocation db on the Aspera node to be up-to-date. See wikis:
    https://wiki.humanconnectome.org/display/storage/ConnectomeDB+download+statistics
    https://wiki.humanconnectome.org/display/storage/Useful+SQL+statements+for+analyzing+download+data
    """
    # GB downloaded by country
    # SELECT g.country_name AS Country, SUM(f.bytes_written)/(1024*1024*1024) AS GB FROM aspera_stats_collector.fasp_sessions AS s INNER JOIN aspera_stats_collector.fasp_files AS f ON s.session_id=f.session_id INNER JOIN geolocation.geo AS g ON s.client_addr=g.ip WHERE f.status='completed' GROUP BY g.country_code;

    q = ("SELECT g.country_name AS Country, SUM(f.bytes_written)/(1024*1024*1024) AS GB "
         "FROM aspera_stats_collector.fasp_sessions AS s "
         "INNER JOIN aspera_stats_collector.fasp_files AS f ON s.session_id=f.session_id "
         "INNER JOIN geolocation.geo AS g ON s.client_addr=g.ip "
         "WHERE f.status='completed' GROUP BY g.country_code")

    print "\nExecuting SQL query ..."
    print q

    with app.app_context():
        try:
            aspera_db = get_db_aspera_geo()
            aspera_db.execute(q)
        except pymysql.err.OperationalError as e:
            if e[0] == 2013:
                print "Lost MySQL connection. Retrying ..."
                aspera_db = get_db_aspera_geo()
                aspera_db.execute(q)
            else:
                raise

    geo = {}

    for row in aspera_db:
        country = row[0]
        size = row[1]
        if country is not None and size is not None:
            if size < 1:
                geo[country] = round(size, 2)
            else:
                geo[country] = round(size, 0)

    return geo


def get_cinab_geo():
    size = {  # commas stripped
        'HCP-2013Q1': 2200,
        'HCP-2013Q2': 2800,
        'HCP-2013Q3': 2800,
        'HCP-2013Q1+Q2': 4500,
        'HCP-2013Q1HCP-2013Q2': 4500,
        'HCP-2013Q1HCP-2013Q2HCP-2013Q3': 6800,
        'HCP-UR80': 3200,
        'HCP-UR100': 4000,
        'HCP-500S': 17000,
        'HCP-900S': 38000
    }

    # SELECT shipping_country,drives_ordered,status FROM orders where (status='shipped') ORDER BY shipping_country;
    # SELECT shipping_country,data_ordered FROM orders where status='shipped' or status LIKE '%deliver%';

    q = ("SELECT shipping_country,data_ordered FROM orders "
         "WHERE status='shipped' OR status LIKE '%deliver%'")
    print q

    with app.app_context():
        cinab_db = get_db_cinab()
        cinab_db.execute(q)

    geo = {}

    for row in cinab_db:
        country = row[0]
        release = row[1].replace(',', '')

        if country is u'' or release is u'':
            continue

        if country not in geo:
            geo[country] = size[release]
        else:
            geo[country] += size[release]

    return geo


def combine_geolocation(cinab_orders, aspera_downloads):
    """
    Combine Aspera and CinaB location stats into a single JSON file
    which can be accessed via REST API.
    JSON file contains {'Country1': int, 'Country2': int ...}
    """
    output = dict((k, [cinab_orders[k], aspera_downloads.get(k)])
                  for k in cinab_orders)
    output.update((k, [None, aspera_downloads[k]])
                  for k in aspera_downloads if k not in cinab_orders)

    combined = {}

    for country in output:
        if None not in output[country]:
            combined[country] = output[country][0] + output[country][1]
        elif not output[country][1]:
            combined[country] = output[country][0]
        elif not output[country][0]:
            combined[country] = output[country][1]

    print combined
    # {'Canada': 3, 'United States': 3, 'Australia': 1}

    json_data = []

    # Build JSON file from gathered geolocation info
    for k, v in combined.iteritems():
        country_data = {
            'code': get_country_iso(k),
            'country': k,
            'z': v
        }
        # If not included in dict, set value to 0
        try:
            country_data['downloads'] = aspera_downloads[k]
        except KeyError as e:
            print e
            country_data['downloads'] = 0

        try:
            country_data['orders'] = cinab_orders[k]
        except KeyError as e:
            print e
            country_data['orders'] = 0

        json_data.append(country_data)

    print json_data

    with open(os.path.join(basedir, 'db', 'geo.json'), 'w') as outfile:
        json.dump(json_data, outfile)


def get_country_iso(country_name):
    for c in countries:
        if c.apolitical_name.lower().strip() == country_name.lower().strip():
            return c.alpha2


if __name__ == '__main__':
    # Update Connectome user and DUT counts
    collect_connectomedb_stats()

    # Collect download history
    collect_aspera_stats()

    # Get Aspera downloads and CinaB orders by location
    collect_geolocation()

    # Connectome-in-a-Box order history are direct queries to MediaTemple db
    # hosted for http://orders.humanconnectome.org
