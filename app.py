import json 

from db import db
from db import Victory
from db import User 
from db import Number
from db import Asset

import users_dao

import datetime
import random

from flask import Flask
from flask import request 

import requests

import os

# Third-party libraries
from flask import Flask, redirect, request, url_for

# google libraries
from google.oauth2 import id_token
from google.auth.transport import requests
import requests

# define db filename 
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
db_filename = "crown.db"

# setup config 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# initialize app
db.init_app(app)
with app.app_context():
    db.create_all()

# generalized response formats 
def success_response(data, code=200):
    """
    Generalized success response function
    """
    return json.dumps(data), code

def failure_response(message, code=404):
    """
    Generalized failure response function
    """
    return json.dumps({"error": message}), code

# -- GOOGLE ROUTES ------------------------------------------------------
@app.route("/api/login/", methods=["POST"])
def login():
    
    #Endpoint for logging a user in with Google and registering new users
    
    data = json.loads(request.data)
    token = data.get("token")
    try:
        
        id_info = id_token.verify_oauth2_token(token, requests.Request(), os.environ.get("CLIENT_ID"))
        email, first_name, last_name = id_info["email"], id_info["given_name"], id_info["family_name"]
        name = first_name + " " + last_name
        
        user = User.query.filter_by(email=email).first()

        if user is None:
            # create user and session
            user = User(email=email, name=name)
            db.session.add(user)
            db.session.commit()
        else:
            user.renew_session()
            db.session.commit()

        return success_response(user.serialize())
        # return session serialize
    except ValueError:
        raise Exception("Invalid Token")

@app.route("/logout/", methods=["POST"])
def logout():
    
   # ?? Endpoint for logging a user out
    
    was_successful, session_token = extract_token(request)
    if not was_successful:
        return session_token
    
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return failure_response("Invalid session token")
    user.session_expiration = datetime.datetime.now()
    db.session.commit()

@app.route("/api/users/<int:user_id>/number/", methods=["POST"])
def add_number(user_id):
    """
    Endpoint for adding phone number to user
    """
    body = json.loads(request.data)
    number = body.get("number")
    if number is None:
        return failure_response("Please input a phone number", 400)
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found", 404)
    user.number = number
    db.session.commit()
    return success_response(user.serialize())


# -- USER ROUTES ------------------------------------------------------
@app.route("/api/users/", methods=["POST"])
def create_user():
    """
    Endpoint for creating a user

    *Used for testing purposes*
    """
    body = json.loads(request.data)
    name=body.get("name")
    email=body.get("email")
    if name is None:
        return failure_response("Please enter something for name", 400)
    if email is None:
        return failure_response("Please enter something for email", 400)
    new_user = User(name=name, email=email)
    db.session.add(new_user)
    db.session.commit()
    return success_response(new_user.serialize(), 201)

@app.route("/api/users/<int:user_id>/")
def get_specific_user(user_id):
    """
    Endpoint for getting user by id 
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    return success_response(user.serialize())

@app.route("/api/users/<int:user_id>/", methods=["DELETE"])
def delete_user(user_id):
    """
    Endpoint for deleting a user 
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    db.session.delete(user)
    db.session.commit()
    return success_response(user.serialize())


# -- VICTORY ROUTES ------------------------------------------------------
@app.route("/api/users/<int:user_id>/victories/")
def get_all_victories(user_id):
    """
    Endpoint for getting all victories
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    return success_response(user.serialize_user_victories())
    
@app.route("/api/users/<int:user_id>/victories/", methods=["POST"])
def create_victory(user_id):
    """
    Endpoint for creating a victory entry
    """
    # checks if user exists
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")

    body = json.loads(request.data)
    date = body.get("date")
    if date is None:
        return failure_response("Please put something for date", 400)  
    description = body.get("description")
    if description is None:
        return failure_response("Please put something for the description", 400) 
    image_data = body.get("image_data")
    if image_data is not None:
        # creates Image object 
        image = Asset(image_data=image_data)
        db.session.add(image)
        db.session.commit()
        new_victory = Victory(date=date,description=description, image_data=image_data)
    else: 
        # creates Victory object 
        new_victory = Victory(date=date,description=description)
    db.session.add(new_victory)
    # adds Victory to user created
    user.user_victories.append(new_victory)
    db.session.commit()
    return success_response(new_victory.simple_serialize(), 201)

@app.route("/api/users/<int:user_id>/victories/<int:victory_id>/")
def get_specific_victory(user_id, victory_id):
    """
    Endpoint for getting a victory by id 
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")

    for victory in user.user_victories:
        if victory.id == victory_id:
            if victory is None:
                return failure_response("Sorry, victory was not found.")
        return success_response(victory.serialize())    
    
           
@app.route("/api/users/<int:user_id>/victories/<int:victory_id>/", methods=["DELETE"])
def delete_victory(user_id,victory_id):
    """
    Endpoint for deleting an victory by id
    """
    # checks if user exists
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    # checks if victory exists
    victory = Victory.query.filter_by(id=victory_id).first()
    if victory is None:
        return failure_response("Victory not found!")
    # checks if user created the victory
    if victory not in user.user_victories:
        return failure_response("User did not create this victory!")
    db.session.delete(victory)
    db.session.commit()
    return success_response(victory.serialize())

@app.route("/api/users/<int:user_id>/victories/<int:victory_id>/", methods=["POST"])
def update_victory(user_id,victory_id):
    """
    Endpoint for updating victory
    """
    body = json.loads(request.data)
    user =  User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    
    for victory in user.user_victories:
        if victory.id == victory_id:
            if victory is None:
                return failure_response("Sorry, victory was not found.")
        victory.description = body.get("description", victory.description)
    
    db.session.commit()
    return success_response(victory.serialize())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)