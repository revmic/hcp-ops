from flask import render_template, request, g, \
    session, flash, redirect, url_for
from forms import RestrictedAccessForm
from app import app
from hcprestricted import search_cdb, has_open_access


@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def hcprestricted():
    form = RestrictedAccessForm()
    email_msg = None
    load_email = False

    ## Handle ConnectomeDB User Search ##
    results = None
    if form.firstname.data and form.lastname.data:
        matches, possible_matches = search_cdb(form.firstname.data, form.lastname.data)

        # TODO - Differentiate exact and partial matches in interface
        if matches:
            results = matches
        elif possible_matches:
            results = possible_matches
        else:
            email_msg = 'please create an account'
            load_email = True

    ## Handle Active Directory Search Button Press ##
    username = request.form.get('search_ad')
    open = False

    if username:  # There was an AD Search button event
        g.username = username
        session['username'] = username
        session['email'] = ''
        open = has_open_access(username)

        if not open:
            email_msg = 'please accept DUT'
            load_email = True

    ## Grant Restricted Access in AD ##
    granted_action = request.form.get('grant_restricted')
    restricted = False

    if granted_action:
        restricted = True
        #open = True
        email_msg = "you've been granted restricted access"
        load_email = True

    ## Handle Email

    form.email.data = email_msg

    return render_template('search.html', form=form, results=results, open=open,
                           restricted=restricted, display_email=load_email)


def button_handler():
    # TODO generalize
    ## Handle Active Directory Search Button Press
    username = None
    open = False
    try:
        username = request.form['search_ad']
    except:
        pass
    if username:
        g.username = username
        open = has_open_access(username)