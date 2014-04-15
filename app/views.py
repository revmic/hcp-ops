from flask import render_template, request, g, session, redirect, url_for, flash
from forms import RestrictedAccessForm, EmailForm
from hcprestricted import *
from config import CC_LIST
from app import app
import json

@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def search():
    form = RestrictedAccessForm()
    open_access = None
    restricted_access = None
    gen_email = False

    ## Handle ConnectomeDB user search event ##
    if request.form.get('search_cdb'):
        session.clear()  # Clear out for multiple additions
    results = None

    if form.firstname.data or form.lastname.data:
        matches, possible_matches = search_cdb(form.firstname.data, form.lastname.data)

        if matches:
            results = matches
            g.exact_match = True
        elif possible_matches:
            results = possible_matches
            g.exact_match = False
        else:
            session['email_msg'] = \
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website I was unable to locate a ConnectomeDB account under your name or evidence that you have already accepted the Open Access Data Use Terms.  To fulfill the conditions of this approval, please take the following steps:\n\n" + \
                "1) Register for a ConnectomeDB account at https://db.humanconnectome.org .\n" + \
                "2) Log into your account and read and accept the Open Access Data Use Terms that you are directed to by the site.\n\n" + \
                "If you already have an account and have accepted the Open Access Data Use Terms, please let me know the username and I will grant access to that account.\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\nRegards,\n\n*FROM*"
            session['firstname'] = form.firstname.data
            session['lastname'] = form.lastname.data
            session['email'] = None
            gen_email = True
    elif not (form.firstname.data or form.lastname.data) and request.form.get('search_cdb'):
        flash("You must enter at least a first or last name to search.", 'warning')

    ## Handle AD search button event ##
    user_select_action = request.form.get('search_ad')

    if user_select_action:  # There was an AD Search button event
        # The action value is a dict that gets returned as a string
        # So, convert the dict string to a json string and back to Python dict
        user_json = user_select_action.replace("u'", '"').replace("'", '"')
        user = json.loads(user_json)
        g.username = user.get('login')
        session['username'] = user.get('login')
        session['email'] = user.get('email')
        session['firstname'] = user.get('firstname')
        session['lastname'] = user.get('lastname')
        open_access = has_open_access(session['username'])
        restricted_access = has_restricted_access(session['username'])

        if not open_access:
            session['email_msg'] = \
                "FYI, your request for access to restricted HCP data has been approved conditional on your additional acceptance of the HCP Open Access Data Use Terms.  On the ConnectomeDB website I found an account '"+session['username']+"' that appears to be yours, but the Open Access Data Use Terms had not been accepted.  To fulfill the conditions of this approval, please log into your account and read and accept the HCP Open Access Data Use Terms that you are directed to by the site.  If you are unable to access your account because the account hasn't been verified, please click the 'Resend email verification' link next to the 'Log In' button.  Please let me know when you have accepted the Open Access terms and I will grant access to the restricted data.\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\nRegards,\n\n*FROM*"
            gen_email = True


    ## Grant Restricted Access in AD ##
    granted_action = request.form.get('grant_restricted')

    if granted_action:  # Grant Restricted Access event
        #print session['username']
        retval = grant_restricted_access(session['username'])
        if retval == True:
            session['email_msg'] = \
                "Per approval of your application for access to Restricted Access HCP data, I've granted access to restricted data to your '"+session['username']+"' account on https://db.humanconnectome.org .\n\n" + \
                "As a reminder, because of the sensitivity of Restricted Data, please do not forward it to others in your laboratory; when their Restricted Access application is submitted and approved, they will be able to access the data themselves.\n\n" + \
                "Please feel free to contact me if you have any questions or are unable to access the restricted data.\n\nRegards,\n\n*FROM*"
            gen_email = True

        restricted_access = has_restricted_access(session['username'])
        open_access = has_open_access(session['username'])


    ## Render email template ##
    generate_email_action = request.form.get('gen_email')

    if generate_email_action:
        # Populate user session variables if nothing was found

        for sender in form.generate_email_as.choices:
            if sender[0] == form.generate_email_as.data:
                session['sender_name'] = sender[1]
        session['sender_email'] = form.generate_email_as.data

        return redirect(url_for('email'))

    return render_template('search.html', form=form, results=results, open_access=open_access,
                           restricted_access=restricted_access, gen_email=gen_email)

@app.route('/email', methods=['GET', 'POST'])
def email():
    form = EmailForm()

    try:
        if session['email'].endswith('.ed'):
            session['email'] += 'u'
    except:
        print "Error appending 'u' to email"

    salutation = 'Dr. ' + session['lastname']
    message = salutation + ',\n\n' + session['email_msg']

    if request.method == 'POST':
        print form.email_to.data
        if not form.email_to.data:
            flash("You forgot to enter a To: address.", 'warning')
            return redirect(url_for('email'))

        send_to = []
        send_to.append(form.email_to.data)
        retval = send_email(subject='Access to Restricted Data in ConnectomeDB',
                            recipients=send_to,
                            sender=form.email_from.data,
                            message=form.email_body.data)
        print retval

        if retval == 1:
            flash('Your message to %s %s at %s has been sent!' %
                  (session['firstname'], session['lastname'], form.email_to.data), 'success')
            return redirect(url_for('search'))
        else:
            flash(retval)
            return redirect(url_for('email'))

    # These need loaded after checking for POST so any changed values will be reflected
    form.email_to.data = session['email']
    form.email_body.data = message.replace('*FROM*', session['sender_name'])
    form.email_from.data = session['sender_email']
    form.email_cc.data = ','.join(CC_LIST)

    return render_template('email.html', form=form)
