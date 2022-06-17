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

class User(db.Model):
    """
    User model 

    one-to-many relationships with victories table
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    number = db.Column(db.Integer, nullable=True)

    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

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
            "number": self.number
        }


class Number(db.Model):
    """
    Phone number model

    one-to-one with user
    """
    
    __tablename__ = "numbers"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.Integer, db.ForeignKey("user.id"),  nullable=False)

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

    __tablename__ = "victory"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)


    def _init_(self, **kwargs):
        """
        Initialize Victory object
        """
        self.date = kwargs.get("date")
        self.description = kwargs.get("description")
        self.image_id = kwargs.get("image_id")
        
    def serialize(self):
        """
        Serializes Victory object
        """
        asset = Asset.query.filter_by(id=self.image_id).first()
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "image": asset.serialize()
        }


EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-2.amazonaws.com" 

class Asset(db.Model):
    """
    Asset Model

    Has a one-to-one relationship with Victory table
    """
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=True)
    salt =  db.Column(db.String, nullable=False)
    extension =  db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)

    def __init__(self,**kwargs):
        """
        Initializes an Asset object/entry
        """
        self.victory_id = kwargs.get("victory_id")
        self.create(kwargs.get("image_data"))

    def serialize(self):
        """
        Serialize Asset object
        """
        return f"{self.base_url}/{self.salt}.{self.extension}"

    def victory_serialize(self):
        """
        Serialize Asset object
        """
        return f"{self.base_url}/{self.salt}.{self.extension}"

    def create(self, image_data):
        """
        Given an image in base64 form, it
        1. Rejects the image is the filetype is not supported file type
        2. Generates a random string for the image file name
        3. Decodes the image and attempts to upload it to AWS
        """
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]

            #only accepts supported file types
            if ext not in EXTENSIONS:
                raise Exception(f"Unsupported file type: {ext}")


            #generate random strong name for file
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase+ string.digits
                )
                for _ in range(16)
            )

            #decode the image and upload to aws
            #remove header of base64 string
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height

            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)

        except Exception as e:
            print(f"Error when creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempt to upload the image to the specified S3 bucket
        """
        try:
            # save image temporarily on server
            img_temploc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temploc)
            
            # upload image to S3
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET_NAME, img_filename)

            # make s3 image url is public
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            # removes image from server
            os.remove(img_temploc)


        except Exception as e:
            print(f"Error when uploading image: {e}")


