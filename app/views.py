from functools import wraps
from datetime import datetime
import re

from flask import (render_template, request, Response, g, session, redirect,
                   url_for, flash, jsonify, json, send_from_directory, )
#from flask.ext.basicauth import BasicAuth
from flask.ext.login import login_required, login_user, logout_user, current_user

from forms import RestrictedAccessForm, EmailForm, LoginForm
from config import CC_LIST, RELAY_HOSTNAMES, basedir, config as cp
from app import app, login_manager
from model import User, get_db_cinab
from hcprestricted import *
from ccfreport import *

#log = open('/tmp/debug-auth.log', 'a')

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.before_request
def before_request():
    g.user = current_user

@login_manager.unauthorized_handler
def unauthorized():
    form = LoginForm()
    flash('You must login to access this page.', 'warning')
    return redirect(url_for('login'))
    #return render_template('login.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        print g.user.id + " appears to already be logged in"
        return redirect(url_for('search'))
    
    form = LoginForm()

    #if form.validate_on_submit():
    if request.method == 'POST':
        user = User(form.username.data, form.password.data)

        if form.username.data == User.id and form.password.data == User.password:
            login_user(user, remember=True)
            return redirect(url_for('search'))
        else:
            flash('Login failed', 'warning')
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/relays', methods=['GET'])
def relays():
    return render_template('relays.html', title='Relay Monitor')
    
# @app.route('/', methods=['GET', 'POST'])
@app.route('/restricted', methods=['GET', 'POST'])
@login_required
def search():
    form = RestrictedAccessForm()
    open_access = None
    restricted_access = None
    gen_email = False

    # Handle ConnectomeDB user search event #
    if request.form.get('search_cdb'):
        session.clear()  # Clear out for multiple additions
    results = None

    if form.firstname.data or form.lastname.data or form.username.data or form.email.data:
        exact_matches, possible_matches = search_cdb(form)

        if exact_matches:
            results = exact_matches
            g.exact_match = True
        else:
            results = possible_matches
            g.exact_match = False
            gen_email = True

        # Only populate session with this if there's a search action, otherwise
        # session variables get incorrectly set for other actions
        if request.form.get('search_cdb'):
            session['email_msg'] = \
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website, I was unable to locate a ConnectomeDB account under your name or evidence that you have already accepted the Open Access Data Use Terms.  To fulfill the conditions of this approval, please take the following steps and respond to this email when completed:\n\n" + \
                "1) Register for a ConnectomeDB account at https://db.humanconnectome.org .\n" + \
                "2) Log into your account and read and accept the Open Access Data Use Terms that you are directed to by the site.\n\n" + \
                "If you already have an account and have accepted the Open Access Data Use Terms, please let me know the username and I will grant access to that account.\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\nRegards,\n\n*FROM*"
            session['status'] = 'No Account'
            session['firstname'] = form.firstname.data
            session['lastname'] = form.lastname.data
            session['email'] = ''
            session['username'] = ''

    elif not (form.firstname.data or form.lastname.data or form.username.data or form.email.data) \
        and request.form.get('search_cdb'):
        flash("You must enter a name, username, or email to search.", 'warning')

    # Handle AD search button event #
    user_select_action = request.form.get('search_ad')

    if user_select_action:  # There was an AD Search button event
        # The action value is a dict that gets returned as a string
        # So, we need to evaluate the string to get a dict
        import ast
        user = ast.literal_eval(user_select_action)

        g.username = user.get('login')
        session['username'] = user.get('login')
        session['email'] = user.get('email')
        session['firstname'] = user.get('firstname')
        session['lastname'] = user.get('lastname')
        open_access = has_group_membership(session['username'],
                                           'Phase2OpenUsers')
        restricted_access = has_group_membership(session['username'],
                                                 'Phase2ControlledUsers')

        if not open_access:
            session['email_msg'] = \
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website, I found an account '" + \
                session[
                    'username'] + "' that appears to be yours, but the Open Access Data Use Terms had not been accepted.  To fulfill the conditions of this approval, please log into your account and read and accept the HCP Open Access Data Use Terms that you are directed to by the site.  If you are unable to access your account because the account hasn't been verified, please click the 'Resend email verification' link next to the 'Log In' button.  Please let me know when you have accepted the Open Access terms and I will grant access to the restricted data.\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\nRegards,\n\n*FROM*"
            session['username'] = user.get('login')
            session['status'] = 'No DUT'
            gen_email = True

    # Grant Restricted Access in AD #
    granted_action = request.form.get('grant_restricted')

    if granted_action:  # Grant Restricted Access event
        retval = grant_restricted_access(session['username'])
        if retval == True:
            session['email_msg'] = \
                "Per approval of your application for access to Restricted Access HCP data, I've granted access to restricted data to your '" + \
                session['username'] + "' account on https://db.humanconnectome.org .\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\n" + \
                "Please feel free to contact me if you have any questions or are unable to access the restricted data.\n\nRegards,\n\n*FROM*"
            session['status'] = 'Access Granted'
            gen_email = True
        else:
            flash(retval, 'danger')

        restricted_access = has_group_membership(session['username'],
                                                 'Phase2ControlledUsers')
        open_access = has_group_membership(session['username'],
                                           'Phase2OpenUsers')

    # Render email template #
    generate_email_action = request.form.get('gen_email')

    if generate_email_action:
        # Populate user session variables if nothing was found
        # update_db(session) # Test w/o actually emailing

        for sender in form.generate_email_as.choices:
            if sender[0] == form.generate_email_as.data:
                session['sender_name'] = sender[1]
        session['sender_email'] = form.generate_email_as.data

        return redirect(url_for('email'))

    return render_template('search.html', form=form, results=results,
                           open_access=open_access,
                           restricted_access=restricted_access,
                           gen_email=gen_email)


@app.route('/email', methods=['GET', 'POST'])
@login_required
def email():
    form = EmailForm()
    salutation = 'Dr. ' + session['lastname']
    message = salutation + ',\n\n' + session['email_msg']

    if request.method == 'POST':
        print form.email_to.data
        if not form.email_to.data:
            flash("You forgot to enter a To: address.", 'warning')
            return redirect(url_for('email'))

        send_to = [form.email_to.data]
        retval = send_email(subject='Access to Restricted Data in ConnectomeDB',
                            recipients=send_to,
                            sender=form.email_from.data,
                            message=form.email_body.data)
        print retval

        if retval == 1:
            flash('Your message to %s %s at %s has been sent! Access DB updated.' %
                  (session['firstname'], session['lastname'], form.email_to.data), 'success')
            # Update DB if email sent successfully
            session['email'] = form.email_to.data
            update_db(session)
            return redirect(url_for('search'))
        else:
            flash(retval)
            return redirect(url_for('email'))

    # These need re-loaded after checking for POST so any changed values will be saved back to form.data
    form.email_to.data = session['email']
    form.email_body.data = message.replace('*FROM*', session['sender_name'])
    form.email_from.data = session['sender_email']
    form.email_cc.data = ','.join(CC_LIST)

    return render_template('email.html', form=form)


@app.route('/restricted/report', methods=['GET', 'POST'])
@login_required
def report():
    form = RestrictedAccessForm()
    db = get_db()

    results = []
    query = db.execute("SELECT * FROM restrictedaccess ORDER BY status_updated,lastname")
    for r in query:
        results.append(r)

    db.close()
    return render_template('report.html', results=results, form=form)


@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    return render_template('config.html')


@app.route('/stats/geolocation')
def geolocation():
    json_data = open(os.path.join(basedir, "db", "geo.json"), "r")
    json_obj = json.load(json_data)
    return jsonify(results=json_obj)


@app.route('/stats/downloads')
def aspera_downloads():
    json_data = open(os.path.join(basedir, "db", "aspera.json"), "r")
    json_obj = json.load(json_data)
    return jsonify(json_obj)


@app.route('/stats', methods=['GET'])
def statistics():
    cdb_file = open(os.path.join(basedir, "db", "dut.json"), "r")
    cdb_stats = json.load(cdb_file)

    aspera_file = open(os.path.join(basedir, "db", "aspera.json"), "r")
    aspera_stats = json.load(aspera_file)

    return render_template('stats.html', cinab_stats=get_cinab_stats(),
                           cdb_stats=cdb_stats, aspera_stats=aspera_stats)


@app.route('/stats/ccf/generate', methods=['POST'])
def download_ccf_report():
    # The method and variables are declared in ccfreport.py
    generate_ccf_report()
    return "Your report is available here:\n" + \
        "https://hcp-ops.humanconnectome.org/static/download/ccf-report.csv"


def get_cinab_stats():
    """
    Builds a map of CinaB stats to pass to the view
    """
    cinab_stats = {
        'customer_count': 0,
        'domestic_customer_count': 0,
        'intl_customer_count': 0,
        'countries': 0,
        'data_size': 0,
        'total_orders': 0,
        'total_drives': 0,
    }

    try:
        db = get_db_cinab()
    except Exception as e:
        print e
        print "Something went wrong connecting to CinaB Orders database"
        return cinab_stats

    # Customer Count
    # SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status FROM orders where (status !='incomplete') and (status!='failed') and (status!='cancel') and (status!='refund') and order_type='data' GROUP BY customer_email ORDER BY customer_email
    q = ("SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status "
         "FROM orders where (status !='incomplete') and (status!='failed') "
         "and (status!='refund') and order_type='data' "
         "GROUP BY customer_email ORDER BY customer_email")
    r = db.execute(q)
    cinab_stats['customer_count'] = r
    # cinab_stats['customer_count'] = len(r)
    #for item in r:
    #    print item

    # International Customers
    # SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status FROM orders where (status !='incomplete') and (status!='failed') and (status!='refund') and (shipping_country!='United States') and order_type='data' GROUP BY customer_email ORDER BY customer_email;
    q = ("SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status "
         "FROM orders where (status !='incomplete') and (status!='failed') "
         "and (status!='refund') and (shipping_country!='United States') and order_type='data' "
         "GROUP BY customer_email ORDER BY customer_email")
    r = db.execute(q)
    cinab_stats['intl_customer_count'] = r

    # Different Countries
    q = "SELECT count(distinct shipping_country) FROM orders where status='shipped'"
    r = db.execute(q)
    cinab_stats['countries'] = db.fetchone()[0]

    # Number of Drives & Data Size
    # SELECT inv.serial, inv.release_id, releases.data_size FROM drive_inventory as inv,releases WHERE inv.drive_status='shipped' AND inv.release_id=releases.release_id GROUP BY serial;
    q = ("SELECT inv.serial, inv.release_id, releases.data_size FROM drive_inventory as inv,releases "
         "WHERE inv.drive_status='shipped' AND inv.release_id = releases.release_id GROUP BY serial")
    r = db.execute(q)
    cinab_stats['total_drives'] = r

    data_size = 0
    for row in db:
        # Adds up all drive sizes, e.g., '4 TB'
        data_size += float(row[2].split(' ')[0])
    cinab_stats['data_size'] = data_size / 1000

    # Total Orders
    q = ("SELECT status FROM orders WHERE (status !='incomplete') and (status != 'pending') "
         "and (status!='failed') and (status!='refund') and (order_type='data')")
    r = db.execute(q)
    cinab_stats['total_orders'] = r

    cinab_stats['domestic_customer_count'] = \
        cinab_stats['customer_count'] - cinab_stats['intl_customer_count']

    return cinab_stats


@app.route('/api/relay/missing-raw')
def relay_missing_raw():
    stats_path = os.path.join(basedir, "db", "relays")
    with open(os.path.join(stats_path, "intradb-backup-uuids.json")) as f:
        resp = f.read()
    return resp


@app.route('/api/relay/hosts/<hostname>/<resource>/<response_format>')
def relay_sessions(hostname, resource='sessions', response_format='json'):
    stats_path = os.path.join(basedir, "db", "relays")

    fname = "{0}-xnat-{1}.{2}".format(hostname, resource, response_format)
    with open(os.path.join(stats_path, fname)) as f:
        items = f.read()

    #if resource == 'xsync-history':
    #    items = filter_xsync_history(items)

    return items


def filter_xsync_history(history):
    non_empty_transfers = []

    for item in json.loads(history):
        if int(item['totalDataSynced']) > 0:
            non_empty_transfers.append(item.encode('utf-8'))

    return non_empty_transfers


@app.route('/api/relay/hosts/<hostname>/nodes/<nodename>/<action>')
def relay_nodes(hostname, nodename, action):
    stats_path = os.path.join(basedir, "db", "relays")
    all_stats = []

    fname = "{0}-{1}-{2}.txt".format(hostname, nodename, action)
    with open(os.path.join(stats_path, fname)) as f:
        mars_files = f.read()
    return mars_files


# API for image relay monitor
@app.route('/api/relay/transfers', methods=['GET', 'POST'])
def relay_transfers():
    if request.method == 'POST':
        try:
            f = request.files['file']
            f.save(request.args.get('filename'))
        except Exception as e:
            return "<h2>" + str(e) + "</h2>", 500
        return "<h2>"+ "success" +"</h2>", 200

    json_path = os.path.join(basedir, "db", "relays")
    all_statuses = []

    for hostname in natural_sort(RELAY_HOSTNAMES):
        fname = "{0}-MARS-status.json".format(hostname)
        with open(os.path.join(json_path, fname)) as f:
            try:
                mars_data = json.load(f)
            except ValueError as e:
                mars_data = {
                    'status': 'Python ValueError.',
                    'message': 'Corrupt MARS status file.',
                    'last-updated': str(datetime.now()),
                    'elapsed': '0'
                }

        fname = "{0}-RAW-status.json".format(hostname)
        with open(os.path.join(json_path, fname)) as f:
            try:
                relay_data = json.load(f)
            except ValueError as e:
                relay_data = {
                    'status': 'Python ValueError.', 
                    'message': 'Corrupt RELAY status file.', 
                    'last-updated': str(datetime.now()),
                    'elapsed': '0'
                }

        mars_elapsed = getElapsedStr(mars_data)
        relay_elapsed = getElapsedStr(relay_data)

        mars_sync = {
            'status': mars_data['status'],
            'message': mars_data['message'],
            'elapsed': mars_elapsed,
            'lastUpdated': mars_data['last-updated']
        }
        relay_sync = {
            'status': relay_data['status'],
            'message': relay_data['message'],
            'elapsed': relay_elapsed,
            'lastUpdated': relay_data['last-updated']
        }
        host_status = {
            'host': hostname, 
            'mars-sync': mars_sync, 
            'relay-sync': relay_sync
        }
        all_statuses.append(host_status)
        
    return jsonify(results=all_statuses)


def getElapsedStr(data):
    elapsed = ""
    try:
        seconds = int(data['elapsed'])
        if seconds < 60:
            elapsed = str(seconds) + " seconds"
        elif seconds < 3600:
            elapsed = str(seconds/60) + " minutes"
        else:
            elapsed = str(seconds/60/60) + " hours"
    except Exception as e:
        print e.message

    return elapsed


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)
