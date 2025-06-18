#App routes
from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
from models.models import *
from flask import current_app as app
import os
import matplotlib
matplotlib.use('Agg')  # Use Anti-Grain Geometry backend (no GUI)
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def signin():
    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")
        usr=UserInfo.query.filter_by(email=uname,password=pwd).first()
        if usr and usr.password=="admin1": #Existed and admin
            return redirect(url_for("admin_dashboard",name=uname))
        elif usr:
            return redirect(url_for("user_dashboard",email=uname))
        else:
            return render_template("login.html", msg="Invalid user credentials...")
        
    return render_template("login.html",msg="")

@app.route("/register", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")
        fullname=request.form.get("fullname")
        address=request.form.get("address")
        pin=request.form.get("pincode")
        usr=UserInfo.query.filter_by(email=uname,password=pwd).first()
        if usr:
            return render_template("signup.html",msg="Soory, this mail already registered!!")
        new_usr=UserInfo(email=uname,password=pwd,fullname=fullname,address=address,pin_code=pin)
        db.session.add(new_usr)
        db.session.commit()
        return render_template("login.html",msg="Registration Successfull, try login now!")
    return render_template("signup.html",msg="")

#Common route for admin dashbaord
@app.route("/admin/<name>")
def admin_dashboard(name):
    user = UserInfo.query.filter_by(email=name).first() 
    parkinglots=get_parkinglots()
    updated_parkinglots = mark_spot_status(parkinglots)
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        lot.available_count = sum(1 for s in spots if s.status == 'A')
        lot.occupied_count = sum(1 for s in spots if s.status == 'O')

    return render_template("admin_dash.html",name=name,parkinglots=updated_parkinglots, user=user)

#common route for user dashboard
@app.route("/user/<email>")
def user_dashboard(email):
    user = get_user_by_email(email)
    if not user:
        return "User not found", 404

    reservations = get_user_reservations(user.id)
    parkinglots = get_all_parking_lots()

    return render_template("user_dash.html", user=user, reservations=reservations, parkinglots=parkinglots)



@app.route('/admin/summary/<name>')
def admin_summary(name):
    parkinglots = ParkingLot.query.all()
    user = UserInfo.query.filter_by(email=name).first() 
    # --- 1. Revenue Pie Chart ---
    labels = []
    revenues = []

    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        total_revenue = 0
        for spot in spots:
            reservations = ReserveParkingSpot.query.filter_by(spot_id=spot.id).all()
            for res in reservations:
                total_revenue += res.parking_cost_per_unit or 0
        labels.append(lot.prime_location_name)
        revenues.append(total_revenue)

    plt.figure(figsize=(5, 5))
    plt.pie(revenues, labels=labels, autopct='%1.1f%%')
    plt.title('Revenue from Each Parking Lot')
    plt.tight_layout()
    pie_buf = BytesIO()
    plt.savefig(pie_buf, format='png')
    pie_buf.seek(0)
    pie_path = os.path.join('static', 'pie_chart.png')
    with open(pie_path, 'wb') as f:
        f.write(pie_buf.read())
    plt.close()

    # --- 2. Occupied vs Available Bar Chart ---
    occupied_counts = []
    available_counts = []
    labels = []

    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        occupied = 0
        available = 0
        for spot in spots:
            latest = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
            if latest:
                occupied += 1
            else:
                available += 1
        occupied_counts.append(occupied)
        available_counts.append(available)
        labels.append(lot.prime_location_name)

    x = range(len(labels))
    plt.figure(figsize=(6, 4))
    plt.bar(x, available_counts, width=0.4, label='Available', color='green')
    plt.bar([i + 0.4 for i in x], occupied_counts, width=0.4, label='Occupied', color='red')
    plt.xticks([i + 0.2 for i in x], labels, rotation=45)
    plt.legend()
    plt.title('Occupied vs Available Spots')
    bar_buf = BytesIO()
    plt.tight_layout()
    plt.savefig(bar_buf, format='png')
    bar_buf.seek(0)
    bar_path = os.path.join('static', 'bar_chart.png')
    with open(bar_path, 'wb') as f:
        f.write(bar_buf.read())
    plt.close()

    return render_template('admin_summary.html',name=name,parkinglots=parkinglots,user=user)


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
        usage_count['No Reservations'] = 1

    labels = list(usage_count.keys())
    sizes = list(usage_count.values())

    # Pie chart
    plt.figure(figsize=(5, 5))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=plt.cm.Paired.colors)
    plt.title("User Spot Usage Summary")
    pie_path = os.path.join("static", "user_spot_summary_pie.png")
    plt.savefig(pie_path)
    plt.close()

    # Bar chart
    plt.figure(figsize=(8, 5))
    wrapped_labels = [label.replace(" ", "\n") for label in labels]
    plt.barh(wrapped_labels, sizes, color="skyblue")
    plt.title("Parking Usage Per Lot")
    plt.ylabel("No. of Reservations")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    bar_path = os.path.join("static", "user_spot_summary_bar.png")
    plt.savefig(bar_path)
    plt.close()

    return render_template("user_summary.html",user=user,name=user.fullname)


def mark_spot_status(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        for spot in spots:
            # reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).first()
            reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
            spot.status = 'O' if reservation else 'A'
        lot.parkingspot = spots  # this is key
    return parkinglots


@app.route("/parkinglot/<name>", methods=["POST","GET"])
def add_lot(name):
    if request.method=="POST":
        # Check if it's JSON data
        if request.is_json:
            data = request.get_json()
            pname = data.get('prime_location_name')
            address = data.get('address')
            pin_code = data.get('pin_code')
            price = float(data.get('price'))
            max_spots = int(data.get('maximum_number_of_spots'))
        else:
            # Handle form submission
            pname=request.form.get('prime_location_name')  
            address=request.form.get('address')
            pin_code=request.form.get('pin_code')
            price=request.form.get('price')
            max_spots=int(request.form.get('maximum_number_of_spots'))

        new_lot=ParkingLot(prime_location_name=pname,address=address,pin_code=pin_code,price=price,maximum_number_of_spots=max_spots)    #LHS attribute name in table, RHS is data fetched from form
        db.session.add(new_lot)
        db.session.commit()

        # Auto-create parking spots
        for _ in range(max_spots):
            new_spot = ParkingSpot(lot_id=new_lot.id, status='A')
            db.session.add(new_spot)
        db.session.commit()

        # Return JSON if API, or redirect if form
        if request.is_json:
            return jsonify({
                "message": "Parking lot and spots created",
                "lot_id": new_lot.id,
                "spots_created": max_spots
            }), 201
        else:
            return redirect(url_for("admin_dashboard",name=name))

    return render_template("AddLot.html",name=name)


@app.route("/search/<name>", methods=["GET","POST"])
def search(name):
    if request.method=="POST":
        search_txt=request.form.get("search_txt")
        by_lot=search_by_user_id(search_txt)
        by_location=search_by_location(search_txt)
        by_pincode=search_by_pincode(search_txt)
        if by_lot:
            return render_template("admin_dash.html",name=name,parkinglots=by_lot)
        elif by_location:
            return render_template("admin_dash.html",name=name,parkinglots=by_location)
        elif by_pincode:
            return render_template("admin_dash.html",name=name,parkinglots=by_pincode)
        
    return redirect(url_for("admin_dashboard",name=name))

@app.route("/user_search/<email>", methods=["GET", "POST"])
def user_search(email):
    user = UserInfo.query.filter_by(email=email).first_or_404()
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        search_type = request.form.get("search_type")

        if search_type == "location":
            parkinglots = search_by_location(search_txt)
        elif search_type == "pin_code":
            parkinglots = search_by_pincode(search_txt)
        else:
            parkinglots = []

        if parkinglots:
            parkinglots = compute_available_spots(parkinglots)

        return render_template("user_dash.html", user=user, email=email, parkinglots=parkinglots, searched_location=search_txt)
    return redirect(url_for("user_dashboard", email=email))




@app.route("/edit_lot/<id>/<name>", methods=["GET","POST"])
def edit_parkinglot(id,name):
    L=get_parkinglot(id)
    user = UserInfo.query.filter_by(email=name).first()
    if request.method=="POST":
        location=request.form.get("prime_location_name")
        address=request.form.get("address")
        pincode=request.form.get("pincode")
        price=request.form.get("price")
        new_max_spots=int(request.form.get("maximum_number_of_spots"))
        current_spot_count = ParkingSpot.query.filter_by(lot_id=id).count()

        L.prime_location_name=location
        L.address=address
        L.pincode=pincode
        L.price=price
        L.maximum_number_of_spots=new_max_spots
        db.session.commit()

        # If the new spot count is greater, add new spots
        if new_max_spots > current_spot_count:
            for _ in range(new_max_spots - current_spot_count):
                new_spot = ParkingSpot(lot_id=id, status='A')
                db.session.add(new_spot)
            db.session.commit()

        return redirect(url_for("admin_dashboard",name=name))
     
    return render_template("edit_lot.html",parkinglot=L,name=name,user=user)


@app.route("/delete_parkinglot/<int:id>/<name>", methods=["POST"])
def delete_parkinglot(id, name):
    lot = ParkingLot.query.get_or_404(id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=id, status='O').count()
    # Prevent deletion if any spot is occupied
    if occupied_spots > 0:
        flash("Cannot delete lot. Some parking spots are still occupied.", "danger")
        return redirect(url_for("admin_dashboard", name=name))
    
    # Prevent deletion if any reservations exist
    reservations = ReserveParkingSpot.query.filter_by(lot_id=id).count()
    if reservations > 0:
        flash("Cannot delete lot. Reservations exist for this lot.", "danger")
        return redirect(url_for("admin_dashboard", name=name))
    
    # Delete all associated spots first
    ParkingSpot.query.filter_by(lot_id=id).delete()
    db.session.delete(lot)
    db.session.commit()

    flash("Parking lot and all associated spots deleted.", "success")
    return redirect(url_for("admin_dashboard", name=name))


@app.route("/delete_spot/<id>/<name>", methods=["GET","POST"])
def delete_parkingspot(id,name):
    S=get_parkingspot(id)
    db.session.delete(S)
    db.session.commit()
    return redirect(url_for("admin_dashboard",name=name))


@app.route("/edit_spot/<id>/<name>", methods=["GET","POST"])
def edit_parkingspot(id,name):
    S=get_parkingspot(id)
    if request.method=="POST":
        spot_id=request.form.get("id")
        Status=request.form.get("status")
        S.id=spot_id
        S.status=Status
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=name))
     
    return render_template("edit_spot.html",spot=S,name=name)

@app.route("/edit_admin_profile/<id>/<name>", methods=["GET","POST"])
def edit_admin_profile(id,name):
    E=UserInfo.query.get_or_404(id)  # Ensures E is never None
    if request.method=="POST":
        Email=request.form.get("email")
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
        E.email=Email
        E.password=Password
        E.fullname=Fullname
        E.address=Address
        E.pin_code=Pin_code
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=E.email))
     
    return render_template("edit_admin_profile.html",user=E,name=name)

@app.route("/edit_user_profile/<id>/<name>", methods=["GET","POST"])
def edit_user_profile(id,name):
    user=UserInfo.query.get_or_404(id)  # Ensures E is never None
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
        return redirect(url_for("user_dashboard",name=user.email))
     
    return render_template("edit_user_profile.html",user=user,name=name)

@app.route("/admin_profile/<int:user_id>", methods=["GET", "POST"])
def view_admin_profile(user_id):
    user = UserInfo.query.get_or_404(user_id)

    if request.method == "POST":
        user.fullname = request.form.get("fullname")
        user.address = request.form.get("address")
        user.pin_code = request.form.get("pin_code")
        db.session.commit()
        return redirect(url_for("admin_dashboard", name=user.email))  # Or your user dashboard

    return render_template("edit_admin_profile.html", user=user)

@app.route("/user_profile/<int:user_id>", methods=["GET", "POST"])
def view_user_profile(user_id):
    user = UserInfo.query.get_or_404(user_id)

    if request.method == "POST":
        user.fullname = request.form.get("fullname")
        user.address = request.form.get("address")
        user.pin_code = request.form.get("pin_code")
        db.session.commit()
        return redirect(url_for("user_dashboard", name=user.email))  # Or your user dashboard

    return render_template("edit_user_profile.html", user=user)




@app.route('/users')
def registered_users():
    users = UserInfo.query.filter(UserInfo.email != "admin@iitm.ac.in").all()
    return render_template('users.html', users=users)

@app.route("/spot/<int:spot_id>")
def view_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    # Dynamically determine status
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(
        ReserveParkingSpot.parking_timestamp.desc()
    ).first()

    if reservation:
        spot.status = 'O'
    else:
        spot.status = 'A'

    # spot.status = 'O' if reservation else 'A'  # Update status manually here

    return render_template("view_spot.html", spot=spot, reservation=reservation)

@app.route("/delete_spot/<int:spot_id>")
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'O':
        flash("Cannot delete occupied spot.")
        return redirect(url_for('view_spot', spot_id=spot.id))
    db.session.delete(spot)
    db.session.commit()
    return redirect(url_for('admin_dashboard', name='admin'))  # adjust if needed


@app.route("/occupied_details/<int:spot_id>")
def occupied_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    # Get latest reservation for that spot
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()

    if not reservation:
        flash("No reservation found for this spot.")
        return redirect(url_for('view_spot', spot_id=spot_id))

    return render_template("occupied_details.html", spot=spot, reservation=reservation)


# Book Parking Route
@app.route("/book_parking/<int:lot_id>/<email>", methods=['GET', 'POST'])
def book_parking(lot_id, email):
    user = get_user_by_email(email)
    if not user:
        return "User not found", 404
    if request.method == "POST":
        # Extract form data
        spot_id = request.form.get("spot_id")
        user_id = request.form.get("user_id")
        vehicle_number = request.form.get("vehicle_number")
        # Create reservation in DB
        new_reservation = ReserveParkingSpot(
            user_id=user_id,
            parking_spot_id=spot_id,
            vehicle_number=vehicle_number,
            start_time=datetime.now()
        )
        db.session.add(new_reservation)
        # Mark spot as occupied
        spot = ParkingSpot.query.get(spot_id)
        spot.status = 'O'
        db.session.commit()
     # Redirect to dashboard after booking
        return redirect(url_for('user_dashboard', email=email))
    # For GET request, show the form
    lot = get_parking_lot_by_id(lot_id)
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not lot:
        return "Parking Lot not found", 404

    return render_template("book_parking.html", lot_id=lot_id, email=email,  user=user, lot=lot, spot=spot)

# Release Parking Route
@app.route("/release_parking/<int:res_id>/<email>", methods=["GET", "POST"])
def release_parking(res_id, email):
    reservation = ReserveParkingSpot.query.get_or_404(res_id)
    user = UserInfo.query.get_or_404(reservation.user_id)
    spot = reservation.spot  # Using the relationship

    if request.method == "POST":
        # Set leaving time
        reservation.leaving_timestamp = datetime.utcnow()
        # Calculate duration in minutes
        duration_minutes = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 60
        # Calculate cost (rate is per minute/hour based on your system)
        total_cost = round(duration_minutes * reservation.parking_cost_per_unit, 2)

        # Create payment record
        payment_method = request.form.get("payment_method")
        payment = Payment(
            reservation_id=reservation.id,
            amount=total_cost,
            payment_method=payment_method,
            status='Success'  # You could handle failures later
        )
        db.session.add(payment)

        # Update spot status to Available
        spot.status = 'A'
        # Save changes
        db.session.commit()

        flash(f"Parking spot released. Total cost: ₹{total_cost} via {payment_method}", "success")
        return redirect(url_for("user_dashboard", email=email))

    # For GET request
    current_time = datetime.utcnow()
    duration_minutes = (current_time - reservation.parking_timestamp).total_seconds() / 60
    total_cost = round(duration_minutes * reservation.parking_cost_per_unit, 2)

    return render_template(
        "release_parking.html",
        reservation=reservation,
        email=email,
        user=user,
        current_time=current_time,
        total_cost=total_cost
    )



@app.route("/reserve_parking", methods=["POST"])
def reserve_parking():
    spot_id = request.form.get("spot_id")
    user_id = request.form.get("user_id")
    lot_id = request.form.get("lot_id")
    vehicle_no = request.form.get("vehicle_no")
    # Validate and fetch required models
    spot = ParkingSpot.query.get(spot_id)
    user = UserInfo.query.get(user_id)
    if not spot or not user or spot.status == 'O':
        return "Invalid reservation request", 400
    # Mark spot as occupied
    spot.status = 'O'
    parking_cost_per_unit = float(lot_id.price)  # price per minute or unit as defined

    # Reserve the spot
    reservation = ReserveParkingSpot(
        spot_id=spot.id,
        user_id=user.id,
        parking_timestamp=datetime.utcnow(),
        lot_id=lot_id,
        parking_cost_per_unit=parking_cost_per_unit,
        # parking_cost_per_unit=10.0,  # default or calculated
        vehicle_no=vehicle_no 
    )
    db.session.add(reservation)
    db.session.commit()

    return redirect(url_for("user_dashboard", email=user.email))


#other supported function
def get_parkinglots():
    parkinglots = ParkingLot.query.all()
    for lot in parkinglots:
        # Get all spots for this lot
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        # Count how many are available
        available = sum(1 for s in spots if s.status == 'A')
        # Add this info dynamically
        lot.available_spots = available
    return parkinglots

def compute_available_spots(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        lot.available_spots = sum(1 for s in spots if s.status == 'A')
    return parkinglots


def search_by_user_id(search_txt):
    user_id=ParkingLot.query.filter(ParkingLot.id.ilike(f"%{search_txt}%")).all()
    return user_id

def search_by_location(search_txt):
    location=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{search_txt}%")).all()
    return location

def search_by_pincode(search_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{search_txt}%")).all()
    return pin_code

def get_parkinglot(id):
    parkinglot=ParkingLot.query.filter_by(id=id).first()
    return parkinglot

def get_parkingspot(id):
    parkingspot=ParkingSpot.query.filter_by(id=id).first()
    return parkingspot

def get_userprofile(id):
    user=UserInfo.query.filter_by(id=id).first()
    return user


def get_user_by_email(email):
    return UserInfo.query.filter_by(email=email).first()



def get_user_reservations(user_id):
    return ReserveParkingSpot.query.filter_by(user_id=user_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).all()

def get_all_parking_lots():
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = sum(1 for spot in lot.parkingspot if spot.status == 'A')  # assuming 'A' = Available
    return lots

def get_parking_lot_by_id(lot_id):
    return ParkingLot.query.get(lot_id)

def get_reservation_by_id(res_id):
    return ReserveParkingSpot.query.get(res_id)

