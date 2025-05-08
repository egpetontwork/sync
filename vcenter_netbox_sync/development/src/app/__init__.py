from flask_wtf import FlaskForm
from wtforms import SubmitField

class SyncForm(FlaskForm):
    submit = SubmitField('Trigger Synchronization')