from functools import wraps

from flask import (render_template, request, Response, g, session, redirect,
                   url_for, flash, jsonify, json, )
from forms import RestrictedAccessForm, EmailForm

from hcprestricted import *
from config import CC_LIST, basedir, config as cp
from app import app
from model import get_db_cinab


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == cp.get('site', 'username') and \
        password == cp.get('site', 'password')


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


# @app.route('/', methods=['GET', 'POST'])
@app.route('/restricted', methods=['GET', 'POST'])
@requires_auth
def search():
    form = RestrictedAccessForm()
    open_access = None
    restricted_access = None
    gen_email = False

    # Handle ConnectomeDB user search event #
    if request.form.get('search_cdb'):
        session.clear()  # Clear out for multiple additions
    results = None

    if form.firstname.data or form.lastname.data:
        exact_matches, possible_matches = search_cdb(form.firstname.data, form.lastname.data)

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
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website I was unable to locate a ConnectomeDB account under your name or evidence that you have already accepted the Open Access Data Use Terms.  To fulfill the conditions of this approval, please take the following steps and respond to this email when completed:\n\n" + \
                "1) Register for a ConnectomeDB account at https://db.humanconnectome.org .\n" + \
                "2) Log into your account and read and accept the Open Access Data Use Terms that you are directed to by the site.\n\n" + \
                "If you already have an account and have accepted the Open Access Data Use Terms, please let me know the username and I will grant access to that account.\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\nRegards,\n\n*FROM*"
            session['status'] = 'No Account'
            session['firstname'] = form.firstname.data
            session['lastname'] = form.lastname.data
            session['email'] = ''
            session['username'] = ''

    elif not (form.firstname.data or form.lastname.data) and request.form.get('search_cdb'):
        flash("You must enter at least a first or last name to search.", 'warning')

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
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website I found an account '" + \
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
@requires_auth
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
@requires_auth
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
@requires_auth
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
    return jsonify(results=json_obj)


@app.route('/stats', methods=['GET'])
def statistics():
    return render_template('stats.html',
                           cdb_stats=get_cdb_stats(),
                           cinab_stats=get_cinab_stats(),
                           aspera_stats=get_aspera_stats())


def get_cdb_stats():
    db = get_db()
    query = "SELECT * FROM access_stats ORDER BY id"
    results = db.execute(query)
    stats = []

    for r in results:
        stats.append(r)

    return stats


def get_cinab_stats():
    """
    Builds a map of CinaB stats to pass to the view
    """
    db = get_db_cinab()

    cinab_stats = {
        'customer_count': 0,
        'domestic_customer_count': 0,
        'intl_customer_count': 0,
        'countries': 0,
        'data_size': 0,
        'total_orders': 0,
        'total_drives': 0,
    }

    # Customer Count
    # SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status FROM orders where (status !='incomplete') and (status!='failed') and (status!='cancel') and (status!='refund') and order_type='data' GROUP BY customer_email ORDER BY customer_email
    q = ("SELECT COUNT(*) AS Rows, customer_email,customer_id,order_type,status "
         "FROM orders where (status !='incomplete') and (status!='failed') "
         "and (status!='refund') and order_type='data' "
         "GROUP BY customer_email ORDER BY customer_email")
    r = db.execute(q)
    cinab_stats['customer_count'] = r
    # cinab_stats['customer_count'] = len(r)
    # for item in r:
    #     print item

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


def get_aspera_stats():
    json_data = open(os.path.join(basedir, "db", "aspera-downloads.json"), "r")
    json_obj = json.load(json_data)
    return json_obj
