import code
from flask_sqlalchemy import SQLAlchemy

import base64
import boto3
import datetime
import io
from io import BytesIO
from mimetypes import guess_extension, guess_type
import os
from PIL import Image
import random
import re
import string

import hashlib

from sqlalchemy import ForeignKey
import bcrypt

db = SQLAlchemy()

user_victories_association_table = db.Table(
    "association_user_victories",
    db.Column("victory_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("victories.id"))
    )

class User(db.Model):
    """
    User model 

    many-to-many relationships with victories table
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    number = db.Column(db.Integer, nullable=True)

    user_victories = db.relationship("Victory",secondary=user_victories_association_table, back_populates="victory_user")

    """
    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)
    """

    def _init_(self, **kwargs):
        """
        Initialize User object/entry
        """
        self.name = kwargs.get("name")
        self.email = kwargs.get("email")
        self.renew_session()

    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token


    def serialize(self):
        """
        Serializes User object
        """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "number": self.number,
            "victories": [v.serialize() for v in self.user_victories]
        }

    def simple_serialize(self):
        """
        Serializes User object
        """
        return {
            "victories": [v.serialize() for v in self.user_victories]
        }

class Number(db.Model):
    """
    Phone number model

    one-to-one with user
    """
    
    __tablename__ = "numbers"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.Integer, db.ForeignKey("users.id"),  nullable=False)

    def _init_(self, **kwargs):
        """
        Initialize Victory object
        """
        self.number = kwargs.get("number")
    
    def serialize(self):
        """
        Serializes Victory object
        """
        return {
            "number": self.number
        }


class Victory(db.Model):
    """
    Victory model 

    many-to-one relationship with user
    """

    __tablename__ = "victories"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=False)

    victory_user = db.relationship("User", secondary=user_victories_association_table, back_populates="user_victories")

    def _init_(self, **kwargs):
        """
        Initialize Victory object
        """
        self.date = kwargs.get("date")
        self.description = kwargs.get("description")
        
    def serialize(self):
        """
        Serializes Victory object
        """
        return {
            "id":self.id, 
            "date": self.date,
            "description": self.description
        }

    def simple_serialize(self):
        """
        Serializes Victory object
        """
        return {
            "date": self.date,
            "description": self.description
        }




EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com" 


