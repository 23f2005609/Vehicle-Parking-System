# Data Models 

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Entity 1 
class UserInfo(db.Model):
    __tablename__ = "userinfo"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.Integer, nullable=False)
    #Relationship
    reserveParkingSpots = db.relationship("ReserveParkingSpot",cascade="all, delete",backref="user",lazy=True) #lazy is for loading the server, cascade all delete if the user gets deleted all tables related to him gets deleted

# Entity 2
class ParkingLot(db.Model):
    __tablename__ = "parkinglot"
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, default=0.0)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    #Relationships
    parkingspot = db.relationship("ParkingSpot",cascade="all, delete",backref="lot",lazy=True) #Parkinglot can access all of its parking spots
    reservations = db.relationship("ReserveParkingSpot",backref="lot",lazy=True) #Parkinglot can access all of its reservations

# Entity 3
class ParkingSpot(db.Model):
    __tablename__ = "parkingspot"
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parkinglot.id'), nullable=False)
    status = db.Column(db.String(1))  # 'O' = Occupied, 'A' = Available
    #Relationship
    reserveParkingSpots = db.relationship("ReserveParkingSpot",cascade="all, delete",backref="spot",lazy=True) #ParkingSpot can access all of its reservations

# Entity 4: ReserveParkingSpot
class ReserveParkingSpot(db.Model):
    __tablename__ = "reserveparkingspot"
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parkinglot.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parkingspot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('userinfo.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime)
    parking_cost_per_unit = db.Column(db.Float, default=0.0)
    vehicle_no = db.Column(db.String(20), nullable=False)
    #Relationship
    payment = db.relationship('Payment',backref='reservation',uselist=False,cascade='all, delete',passive_deletes=True) #ReserveParkingSpot can access all of its payments

# Entity 5: Payment
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer,db.ForeignKey('reserveparkingspot.id', ondelete='CASCADE'),unique=True,nullable=False)  #when reservation is deleted payment also gets deleted
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
