from flask import  render_template, request, url_for, redirect, flash, jsonify
from models.models import *
from flask import current_app as app
import os
import matplotlib
matplotlib.use('Agg')  # Use Anti-Grain Geometry backend (no GUI)
import matplotlib.pyplot as plt

#common route for user dashboard
@app.route("/user/<email>")
def user_dashboard(email):
    user = get_user_by_email(email)

    reservations = get_user_reservations(user.id)
    parkinglots = get_all_parking_lots()

    return render_template("user_dash.html", user=user, reservations=reservations, parkinglots=parkinglots)

@app.route("/user_search/<email>", methods=["GET", "POST"])
def user_search(email):
    user = UserInfo.query.filter_by(email=email).first()
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        search_type = request.form.get("search_type")

        if search_type == "location":
            parkinglots = search_by_location(search_txt)
        elif search_type == "pin_code":
            parkinglots = search_by_pincode(search_txt)
        else:
            parkinglots = [] #Returns none 

        if parkinglots:
            parkinglots = compute_available_spots(parkinglots)

        return render_template("user_dash.html", user=user, email=email, parkinglots=parkinglots, searched_location=search_txt)
    return redirect(url_for("user_dashboard", email=email))

@app.route("/user_profile/<int:user_id>", methods=["GET", "POST"])
def view_user_profile(user_id):
    user = UserInfo.query.get(user_id)

    if request.method == "POST":
        user.fullname = request.form.get("fullname")
        user.address = request.form.get("address")
        user.pin_code = request.form.get("pin_code")
        db.session.commit()
        return redirect(url_for("user_dashboard", name=user.email)) 

    return render_template("edit_user_profile.html", user=user)


@app.route("/edit_user_profile/<id>/<name>", methods=["GET","POST"])
def edit_user_profile(id,name):
    user=UserInfo.query.get(id)  
    if request.method=="POST":
        Email=request.form.get("email")
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
        user.email=Email
        user.password=Password
        user.fullname=Fullname
        user.address=Address
        user.pin_code=Pin_code
        db.session.commit()
        return redirect(url_for("user_dashboard",email=user.email))
     
    return render_template("edit_user_profile.html",user=user,name=name)


@app.route("/user/summary/<string:email>")
def user_summary(email):
    user = UserInfo.query.filter_by(email=email).first()
    # Fetch user's reservations
    user_reservations = ReserveParkingSpot.query.filter_by(user_id=user.id).all()
    # Prepare data
    lot_names = []
    usage_count = {}

    for res in user_reservations:
        lot = ParkingLot.query.get(res.spot.lot_id)
        if lot:
            lot_names.append(lot.prime_location_name)
            usage_count[lot.prime_location_name] = usage_count.get(lot.prime_location_name, 0) + 1

    if not usage_count:
        usage_count['No Data'] = 0

    labels = list(usage_count.keys())
    sizes = list(usage_count.values())

    # Bar chart
    plt.figure(figsize=(6, 5))
    wrapped_labels = [label.replace(" ", "\n") for label in labels]
    plt.bar(wrapped_labels, sizes, color="skyblue")
    plt.title("Parking Usage Per Lot")
    plt.ylabel("No. of Reservations")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    bar_path = os.path.join("static", "user_spot_summary_bar.png")
    plt.savefig(bar_path)
    plt.close()

    return render_template("user_summary.html",user=user,name=user.fullname)



def get_user_by_email(email):
    return UserInfo.query.filter_by(email=email).first()

def get_user_reservations(user_id):
    return ReserveParkingSpot.query.filter_by(user_id=user_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).all()

def get_all_parking_lots():
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = sum(1 for spot in lot.parkingspot if spot.status == 'A')  # assuming 'A' = Available
    return lots

def search_by_location(search_txt):
    location=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{search_txt}%")).all()
    return location

def search_by_pincode(search_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{search_txt}%")).all()
    return pin_code

def get_userprofile(id):
    user=UserInfo.query.filter_by(id=id).first()
    return user

def compute_available_spots(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        lot.available_spots = sum(1 for s in spots if s.status == 'A')
    return parkinglots
