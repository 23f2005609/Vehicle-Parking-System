from flask import  render_template, request, url_for, redirect, flash
from models.models import *
from flask import current_app as app
import os #used for saving chart files
import matplotlib
matplotlib.use('Agg')  #  Prevents GUI/thread errors
import matplotlib.pyplot as plt

#common route for user dashboard
@app.route("/user/<email>")
def user_dash(email):
    #using helper functions to get user, reservations and parkinglots
    user = user_by_email(email)
    reservations = user_reservations(user.id)
    parkinglots = all_parking_lots()

    return render_template("user_dash.html", user=user, reservations=reservations, parkinglots=parkinglots)

@app.route("/user_search/<email>", methods=["GET", "POST"])
def user_search(email):
    user = UserInfo.query.filter_by(email=email).first() #filtering user by email from db when email matches in url and first ensures it returns single user or none if not found
    if request.method == "POST":
        s_txt = request.form.get("s_txt") # text the user enters to search 
        s_type = request.form.get("s_type") #gets what the user is searching for location, pincode
        # validating if user has searched somewhing or not
        if not s_txt or not s_type:
            flash("Please enter something and select a search type!", "danger")
            return redirect(url_for("user_dash", email=email))

        if s_type == "address":
            parkinglots = find_by_address(s_txt)
        elif s_type == "pin_code":
            parkinglots = find_by_pincode(s_txt)
        elif s_type == "lot_name":
            parkinglots = find_by_lot_name(s_txt)
        else:
            parkinglots = [] #will return empty if not found

        if parkinglots:
            parkinglots = cal_avail_spots(parkinglots) #if parking lot found it updates with avail spots by calling helper function
        
        return render_template("user_dash.html", user=user, email=email, parkinglots=parkinglots, s_txt=s_txt)
    
    return redirect(url_for("user_dash", email=email))


@app.route("/edit_user_profile/<id>/<email>", methods=["GET","POST"]) # id, email are parameters GET- to display form and POST-to submit or update data
def update_user_profile(id,email):
    U=UserInfo.query.get(id)  #gets user with id in userinfo
    if request.method=="POST": #runs when user submitted a form POST
        # gets the data user enterd in form HTML
        Email=request.form.get("email") 
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        phn=request.form.get("phn_no")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
        # it updates db with new records
        U.email=Email
        U.password=Password
        U.fullname=Fullname
        U.phone=phn
        U.address=Address
        U.pin_code=Pin_code
        db.session.commit() #commits data permanently in db
        flash(f"{U.fullname}'s Profile Updated Successfully!", "success")
        return redirect(url_for("user_dash",email=U.email))
    # user first visit or GET req this shows user the html page to let user view or edit
    return render_template("edit_user_profile.html",user=U,email=email)

@app.route("/user/summary/<string:email>")
def summary_user(email):
    user = UserInfo.query.filter_by(email=email).first() #fetches user with email
    reservations = ReserveParkingSpot.query.filter_by(user_id=user.id).all() # Gets all reservation history for that user
    # Bar chart for usage of lots
    payments = Payment.query.filter_by(id=user.id).all() 
    total_parkings = len(reservations)
    total_amount = sum(res.payment.amount if res.payment else 0 for res in reservations)
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
    images_folder = os.path.join('static', 'images') 
    os.makedirs(images_folder, exist_ok=True)#it creates image folder if not present
    plt.figure(figsize=(6, 4))
    wrapped_labels = [label.replace(" ", "\n") for label in labels] #make long lot name by replacing spaces with newlines
    plt.bar(wrapped_labels, sizes, color="blue")
    plt.title("Parking Usage Per Lot")
    plt.ylabel("No. of Reservations")
    plt.xticks(rotation=0, ha='center')
    plt.tight_layout()
    bar_path = os.path.join(images_folder, "user_spot_summary_bar.png")
    plt.savefig(bar_path)
    plt.close()

    #pie chart for spending
    # it fetches all payments by this user by joining Payment and ReserveParking spot
    payments = Payment.query.join(ReserveParkingSpot).filter(ReserveParkingSpot.user_id == user.id).all()
    # Aggregate spending per lot
    spend_per_lot = {}
    for payment in payments:
        lot = payment.reservation.spot.lot if payment.reservation and payment.reservation.spot else None #gets which parking lot payment belongs to
        if lot:
            lot_name = lot.prime_location_name
            spend_per_lot[lot_name] = spend_per_lot.get(lot_name, 0) + payment.amount #{"Lot A": 100, "Lot B": 60} creates a dict
    labels = list(spend_per_lot.keys())
    values = list(spend_per_lot.values())
    images_folder = os.path.join('static', 'images')
    os.makedirs(images_folder, exist_ok=True)
    plt.figure(figsize=(6, 4))
    plt.title("Total ₹ Spent Per Parking Lot")
    if values and any(v > 0 for v in values):
        plt.pie(values,labels=labels, autopct="%1.1f%%", startangle=140, shadow=True)
        # plt.title("Total ₹ Spent Per Parking Lot")
        pie_path = os.path.join("static", "user_spot_summary_pie.png")
        plt.tight_layout()
        plt.savefig(pie_path)
        plt.close()
    else:
        plt.text(0.5, 0.5, "No Data Available !", ha="center", va="center", fontsize=18, color="red")
        pie_path = os.path.join(images_folder, "user_spot_summary_pie.png")
        plt.tight_layout()
        plt.savefig(pie_path)
        plt.close()
    return render_template("user_summary.html",user=user,total_parkings=total_parkings,total_amount=total_amount)

#route where users can see their payment history
@app.route('/user/payments/<email>')
def user_pay(email):
    user = UserInfo.query.filter_by(email=email).first() #fetches single user user based on email
    reservations = ReserveParkingSpot.query.filter_by(user_id=user.id).all()
    payments = [r.payment for r in reservations if r.payment]
    return render_template('user_pay.html', payments=payments, user=user, email=email)

@app.route("/book_parking/<int:lot_id>/<email>", methods=['GET', 'POST'])
def reserve_lot(lot_id, email):
    user = UserInfo.query.filter_by(email=email).first() # it gets user by email
    lot = ParkingLot.query.get(lot_id) # it gets lot by id
    if request.method == "POST":
        # Get values from form
        spot_id = request.form.get("spot_id")
        vehicle_no = request.form.get("vehicle_no")
        # Validate spot
        spot = ParkingSpot.query.get(spot_id)
        if spot.status == 'O':
            return redirect(url_for('reserve_lot', lot_id=lot_id, email=email))
        # Create reservation
        new_reservation = ReserveParkingSpot(
            lot_id=lot.id,
            user_id=user.id,
            spot_id=spot.id,
            vehicle_no=vehicle_no,
            parking_timestamp=datetime.now(),
            parking_cost_per_unit=lot.price
        )
        db.session.add(new_reservation)
        spot.status = 'O'  # now after reservation mark it as occupied
        db.session.commit()

        flash(f"{user.fullname}, your booking is successful!", "success")
        return redirect(url_for('user_dash', email=email))

    # For GET: to find first available parking spot
    avail_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not avail_spot:
        flash("No available parking spots in this lot at the moment!", "danger")
        return redirect(url_for('user_dash', email=email))

    return render_template(
        "book_parking.html",
        lot=lot,
        spot=avail_spot,
        user=user,
        email=email
    )

# Release Parking Route
@app.route("/release_parking/<int:res_id>/<email>", methods=["GET", "POST"])
def release_lot(res_id, email):
    reservation = ReserveParkingSpot.query.get(res_id)
    user = UserInfo.query.get(reservation.user_id) #user_id associated with reservation 
    spot = reservation.spot  # Using the relationship

    if request.method == "POST":
        # Setting leaving time at the time we release the spot
        reservation.leaving_timestamp = datetime.now()
        # Calculate duration in hours
        duration_hrs = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 3600 #sec to hrs
        # Calculate cost (rate is per hour )
        total_cost = round(duration_hrs * reservation.parking_cost_per_unit, 2) # rounding upto 2 decimal places

        payment_method = request.form.get("payment_method")

        # it helps to Prevent duplicate payment insertion
        exist_payment = Payment.query.filter_by(reservation_id=reservation.id).first()
        if not exist_payment:
            #creates new payment record
            payment = Payment(
                reservation_id=reservation.id,
                amount=total_cost,
                payment_method=payment_method,
                status='Success',
                timestamp=datetime.now()
            )
            db.session.add(payment)
        spot.status = 'A' # after release mark it as available
        db.session.commit() # then saving the changes
        flash(f"Parking spot released, Total cost is ₹{total_cost} via {payment_method}", "success")
        return redirect(url_for("user_dash", email=email))

    # For GET request it shows the form details of reservation
    current_time = datetime.now()
    duration_hrs = (current_time - reservation.parking_timestamp).total_seconds() / 3600 #cal in hrs
    total_cost = round(duration_hrs * reservation.parking_cost_per_unit, 2) # round upto 2 decimal places

    return render_template(
        "release_parking.html",
        reservation=reservation,
        email=email,
        user=user,
        current_time=current_time,
        total_cost=total_cost
    )


# Helper Functions 
def user_by_email(email):
    return UserInfo.query.filter_by(email=email).first() #fetches single user user based on email

def user_reservations(user_id):
    #fetches all and most recent reservations made by user
    return ReserveParkingSpot.query.filter_by(user_id=user_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).all()

def all_parking_lots():
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = sum(1 for spot in lot.parkingspot if spot.status == 'A')  # calculates how many spots are available by adding temp attribute .available_spots to each lot
    return lots

def find_by_address(s_txt):
    #searches lot with partial text inputed by user 
    address=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{s_txt}%")).all()
    return address

def find_by_lot_name(s_txt):
    #searches lot with partial text inputed by user 
    lot_names=ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f"%{s_txt}%")).all()
    return lot_names

def find_by_pincode(s_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{s_txt}%")).all()
    return pin_code

def cal_avail_spots(parkinglots):
    for l in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=l.id).all()
        l.available_spots = sum(1 for s in spots if s.status == 'A') #count available spots
    return parkinglots
