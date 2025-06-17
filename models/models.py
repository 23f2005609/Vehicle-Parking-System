# Data Models 

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
#This imports the datetime class from Python’s built-in datetime module so that you can use functions like:


db=SQLAlchemy()

#Entity 1
class UserInfo(db.Model):
    __tablename__="userinfo"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    fullname = db.Column(db.String(100),nullable=False)
    address = db.Column(db.String(200),nullable=False)
    pin_code = db.Column(db.Integer,nullable=False)
    # Relations
    reserveParkingSpots=db.relationship("ReserveParkingSpot",cascade="all,delete",backref="user_info",lazy=True) #lazy is for the loading of server, cascade all delete if the user gets deleted all tables related to him gets deleted, backref is the current table name
    #user can access all of his spots

#Entity 2
class ParkingLot(db.Model):
    __tablename__="parkinglot"
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100),unique=True,nullable=False)
    price = db.Column(db.Float,default=0.0)
    address = db.Column(db.String(200),nullable=False)
    pin_code = db.Column(db.String(10),nullable=False)
    maximum_number_of_spots = db.Column(db.Integer,nullable=False)
    #Relations
    parkingspot=db.relationship("ParkingSpot",cascade="all,delete",backref="parkinglot",lazy=True) #Parkinglot can access all of its parking spots

#Entity 3
class ParkingSpot(db.Model):
    __tablename__="parkingspot"
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parkinglot.id'), nullable=False)
    status = db.Column(db.String(1))  # 'O' = Occupied, 'A' = Available
    reserveparkingspot=db.relationship("ReserveParkingSpot",cascade="all,delete",backref="parkingspot",lazy=True) #Parkingspot can access all of its reserve parking spots
    lot = db.relationship("ParkingLot", backref="spots")  # Add this line

#Entity 4
class ReserveParkingSpot(db.Model):
    __tablename__="reserveparkingspot"
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parkingspot.id'),nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('userinfo.id'),nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow) #default=datetime.utcnow: It ensures the timestamp is set only at the moment of record creation.
    leaving_timestamp = db.Column(db.DateTime)
    parking_cost_per_unit = db.Column(db.Float,default=0.0)
    vehicle_no = db.Column(db.String(20), nullable=False) 
    # Relationships
    user= db.relationship("UserInfo", backref="reservations")
    spot = db.relationship("ParkingSpot", backref="reservations")
    payment = db.relationship('Payment', backref='reservation', uselist=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reserveparkingspot.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # e.g., 'Cash', 'Card', 'UPI'
    status = db.Column(db.String(20), nullable=False)  # e.g., 'Success', 'Pending', 'Failed'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
