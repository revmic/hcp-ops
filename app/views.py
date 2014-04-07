from flask import render_template, flash, redirect, url_for
from forms import SearchConnectomeForm
from app import app


@app.route('/', methods=['GET', 'POST'])
def search_connectome():
    form = SearchConnectomeForm()
    return render_template('index.html', form=form)

    # if form.validate_on_submit():
    #     flash('Your changes have been saved.')
    #     return redirect(url_for('index'))
    # else:
    #     form.firstname.data = None
    #     form.lastname.data = None
