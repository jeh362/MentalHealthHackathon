# code to send notifications/reminders
from db import db
from db import Victory
from db import User 
from db import Number
from db import Asset

from flask import Flask

# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
db_filename = "crown.db"

# setup config 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

# initialize app
db.init_app(app)
with app.app_context():
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)
    users = User.query.all()
    for user in users:
        # Find your Account SID and Auth Token at twilio.com/console
        # and set the environment variables. See http://twil.io/secure
        if user.number is not None:
            message = client.messages.create(
                body="Hello there! Let's not forget some of the amazing things you have done this month go check out the Little Victories app and celebrate YOU!",
                from_='+13254408918',
                to= user.number 
            )