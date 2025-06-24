from flask import  render_template, request, url_for, redirect
from models.models import *
from flask import current_app as app
import os #used for saving chart files
import matplotlib
matplotlib.use('Agg')  #  Prevents GUI/thread errors
import matplotlib.pyplot as plt

#common route for user dashboard
@app.route("/user/<email>")
def user_dashboard(email):
    #using helper functions to get user, reservations and parkinglots
    user = get_user_by_email(email)
    reservations = get_user_reservations(user.id)
    parkinglots = get_all_parking_lots()

    return render_template("user_dash.html", user=user, reservations=reservations, parkinglots=parkinglots)

@app.route("/user_search/<email>", methods=["GET", "POST"])
def user_search(email):
    user = UserInfo.query.filter_by(email=email).first() #filtering user by email from db when email matches in url and first ensures it returns single user or none if not found
    if request.method == "POST":
        search_txt = request.form.get("search_txt") # text the user enters to search 
        search_type = request.form.get("search_type") #gets what the user is searching for location, pincode

        if search_type == "location":
            parkinglots = search_by_location(search_txt)
        elif search_type == "pin_code":
            parkinglots = search_by_pincode(search_txt)
        else:
            parkinglots = [] #Returns empty if not found

        if parkinglots:
            parkinglots = cal_available_spots(parkinglots) #if parking lot found it updates with avail spots by calling helper function

        return render_template("user_dash.html", user=user, email=email, parkinglots=parkinglots, searched_location=search_txt)
    return redirect(url_for("user_dashboard", email=email))


@app.route("/edit_user_profile/<id>/<email>", methods=["GET","POST"]) # id, email are parameters GET- to display form and POST-to submit or update data
def edit_user_profile(id,email):
    user=UserInfo.query.get(id)  #gets user with id in userinfo
    if request.method=="POST": #runs when user submitted a form POST
        # gets the data user enterd in form HTML
        Email=request.form.get("email") 
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
        # updates db with new records
        user.email=Email
        user.password=Password
        user.fullname=Fullname
        user.address=Address
        user.pin_code=Pin_code
        db.session.commit() #commits data permanently in db
        return redirect(url_for("user_dashboard",email=user.email))
    # user first visit or GET req this shows user the html page to let user view or edit
    return render_template("edit_user_profile.html",user=user,email=email)

@app.route("/user/summary/<string:email>")
def user_summary(email):
    user = UserInfo.query.filter_by(email=email).first() #fetches user with email
    # Gets all reservation history for that user
    reservations = ReserveParkingSpot.query.filter_by(user_id=user.id).all()
    lot_names = []
    use_count = {}
    for res in reservations:
        lot = ParkingLot.query.get(res.spot.lot_id) #gets which parking lot reservatrion belongs to
        if lot:
            lot_names.append(lot.prime_location_name)
            use_count[lot.prime_location_name] = use_count.get(lot.prime_location_name, 0) + 1 #{'Lot A':3, 'Lot B':2,..} creates a dict
    # If no reservation it will show no data is available
    if not use_count:
        use_count['No Data'] = 0
    labels = list(use_count.keys())
    sizes = list(use_count.values())
    # Bar chart for usage of lots by user
    plt.figure(figsize=(6, 5))
    wrapped_labels = [label.replace(" ", "\n") for label in labels] #make long lot name by replacing spaces with newlines
    plt.bar(wrapped_labels, sizes, color="skyblue")
    plt.title("Parking Usage Per Lot")
    plt.ylabel("No. of Reservations")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    bar_path = os.path.join("static", "user_spot_summary_bar.png")
    plt.savefig(bar_path)
    plt.close()
    # Fetch all payments by this user by joining Payment and ReserveParking spot
    payments = Payment.query.join(ReserveParkingSpot).filter(ReserveParkingSpot.user_id == user.id).all()
    # Aggregate spending per lot
    spend_per_lot = {}
    for payment in payments:
        lot = payment.reservation.spot.lot if payment.reservation and payment.reservation.spot else None
        if lot:
            lot_name = lot.prime_location_name
            spend_per_lot[lot_name] = spend_per_lot.get(lot_name, 0) + payment.amount #{"Lot A": 100, "Lot B": 60} creates a dict
    labels = list(spend_per_lot.keys())
    values = list(spend_per_lot.values())
    plt.figure(figsize=(6, 5))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=140, shadow=True)
    plt.title("Total ₹ Spent Per Parking Lot")
    pie_path = os.path.join("static", "user_spot_summary_pie.png")
    plt.tight_layout()
    plt.savefig(pie_path)
    plt.close()
    return render_template("user_summary.html",user=user,name=user.fullname)
#route where users can see their payment history
@app.route('/user/payments/<email>')
def user_payment(email):
    user = UserInfo.query.filter_by(email=email).first() #fetches single user user based on email
    reservations = ReserveParkingSpot.query.filter_by(user_id=user.id).all()
    payments = [r.payment for r in reservations if r.payment]
    return render_template('user_pay.html', payments=payments, user=user, email=email)

# Helper Functions 
def get_user_by_email(email):
    return UserInfo.query.filter_by(email=email).first() #fetches single user user based on email

def get_user_reservations(user_id):
    #fetches all and most recent reservations made by user
    return ReserveParkingSpot.query.filter_by(user_id=user_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).all()

def get_all_parking_lots():
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = sum(1 for spot in lot.parkingspot if spot.status == 'A')  # calculates how many spots are available by adding temp attribute .available_spots to each lot
    return lots

def search_by_location(search_txt):
    #searches lot with partial text inputed by user 
    location=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{search_txt}%")).all()
    return location

def search_by_pincode(search_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{search_txt}%")).all()
    return pin_code

def get_userprofile(id):
    user=UserInfo.query.filter_by(id=id).first()
    return user

def cal_available_spots(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        lot.available_spots = sum(1 for s in spots if s.status == 'A') #count available spots
    return parkinglots
