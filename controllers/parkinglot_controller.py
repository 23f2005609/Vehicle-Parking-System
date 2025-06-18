from flask import  render_template, request, url_for, redirect, flash, jsonify
from models.models import *
from flask import current_app as app
from datetime import datetime


@app.route("/parkinglot/<email>", methods=["POST","GET"])
def add_lot(email):
    user = UserInfo.query.filter_by(email=email).first()
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
        # Auto-creates parking spots
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
            return redirect(url_for("admin_dashboard",email=email))

    return render_template("AddLot.html",email=email,user=user)

@app.route("/edit_lot/<id>/<email>", methods=["GET","POST"])
def edit_parkinglot(id,email):
    L=get_parkinglot(id)
    user = UserInfo.query.filter_by(email=email).first()
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

        # If the new spot count is greater than old, add new spots
        if new_max_spots > current_spot_count:
            for _ in range(new_max_spots - current_spot_count):
                new_spot = ParkingSpot(lot_id=id, status='A')
                db.session.add(new_spot)
            db.session.commit()

        return redirect(url_for("admin_dashboard",email=email))
     
    return render_template("edit_lot.html",parkinglot=L,email=email,user=user)


@app.route("/delete_parkinglot/<int:id>/<email>", methods=["POST"])
def delete_parkinglot(id, email):
    lot = ParkingLot.query.get_or_404(id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=id, status='O').count()
    # Don't delete if any spot is occupied
    if occupied_spots > 0:
        flash("Cannot delete lot. Some parking spots are still occupied.", "danger")
        return redirect(url_for("admin_dashboard", email=email))
    
     # Not to delete if there are ACTIVE reservations or not released
    active_reservations = ReserveParkingSpot.query\
        .join(ParkingSpot, ReserveParkingSpot.spot_id == ParkingSpot.id)\
        .filter(ParkingSpot.lot_id == id, ReserveParkingSpot.leaving_timestamp == None).count()  #Firstly linking reservation with its spots so we can access lot_id, then filter lot we want to delete and not to delete the reservations that are still active or not released yet

    if active_reservations > 0:
        flash("Cannot delete lot. Some active reservations still exist.", "danger")
        return redirect(url_for("admin_dashboard", email=email))

    # Delete the reservation history for that lot 
    spot_ids = [s.id for s in ParkingSpot.query.filter_by(lot_id=id).all()]
    ReserveParkingSpot.query.filter(ReserveParkingSpot.spot_id.in_(spot_ids)).delete(synchronize_session=False)
    
    # Delete all spots for the lot first
    ParkingSpot.query.filter_by(lot_id=id).delete()
    db.session.delete(lot)
    db.session.commit()

    return redirect(url_for("admin_dashboard", email=email))


@app.route("/delete_spot/<id>/<email>", methods=["GET","POST"])
def delete_parkingspot(id,email):
    S=get_parkingspot(id)
    db.session.delete(S)
    db.session.commit()
    return redirect(url_for("admin_dashboard",email=email))


@app.route("/edit_spot/<id>/<email>", methods=["GET","POST"])
def edit_parkingspot(id,email):
    S=get_parkingspot(id)
    if request.method=="POST":
        spot_id=request.form.get("id")
        Status=request.form.get("status")
        S.id=spot_id
        S.status=Status
        db.session.commit()
        return redirect(url_for("admin_dashboard",email=email))
     
    return render_template("edit_spot.html",spot=S,email=email)


@app.route("/spot/<int:spot_id>/<email>")
def view_spot(spot_id,email):
    spot = ParkingSpot.query.get_or_404(spot_id)
    # Dynamically determine status
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
    # We are updating spot status base on reservation
    if reservation:
        spot.status = 'O'
    else:
        spot.status = 'A'

    return render_template("view_spot.html", spot=spot, reservation=reservation,email=email)

@app.route("/delete_spot/<int:spot_id>/<email>")
def delete_spot(spot_id,email):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'O':
        flash("Cannot delete occupied spot.")
        return redirect(url_for('view_spot', spot_id=spot.id, email=email))
    db.session.delete(spot)
    db.session.commit()
    return redirect(url_for('admin_dashboard', email=email))  


@app.route("/occupied_details/<int:spot_id>/<email>")
def occupied_details(spot_id,email):
    spot = ParkingSpot.query.get_or_404(spot_id)
    # Get latest reservation for the spot
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()

    if not reservation:
        flash("No reservation found for this spot.")
        return redirect(url_for('view_spot', spot_id=spot_id, email=email))

    return render_template("occupied_details.html", spot=spot, reservation=reservation, email=email)


# Book Parking Route
@app.route("/book_parking/<int:lot_id>/<email>", methods=['GET', 'POST'])
def book_parking(lot_id, email):
    user = get_user_by_email(email)
    if request.method == "POST":
        # Get Data from Form
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
        # Mark spot as occupied after reservation
        spot = ParkingSpot.query.get(spot_id)
        spot.status = 'O'
        db.session.commit()
     # Redirect to dashboard after booking
        return redirect(url_for('user_dashboard', email=email))
    # For GET request, show the form
    lot = get_parking_lot_by_id(lot_id)
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

    return render_template("book_parking.html", lot_id=lot_id, email=email,  user=user, lot=lot, spot=spot)

@app.route("/reserve_parking", methods=["POST"])
def reserve_parking():
    spot_id = request.form.get("spot_id")
    user_id = request.form.get("user_id")
    vehicle_no = request.form.get("vehicle_no")
    # fetch required models
    spot = ParkingSpot.query.get(spot_id)
    lot = ParkingLot.query.get(spot.lot_id) 
    user = UserInfo.query.get(user_id)
    # Mark spot as occupied
    spot.status = 'O'
    # Reserve the spot
    reservation = ReserveParkingSpot(
        spot_id=spot.id,
        user_id=user.id,
        parking_timestamp=datetime.utcnow(),
        parking_cost_per_unit=lot.price,
        vehicle_no=vehicle_no 
    )
    db.session.add(reservation)
    db.session.commit()

    return redirect(url_for("user_dashboard", email=user.email))



# Release Parking Route
@app.route("/release_parking/<int:res_id>/<email>", methods=["GET", "POST"])
def release_parking(res_id, email):
    reservation = ReserveParkingSpot.query.get_or_404(res_id)
    user = UserInfo.query.get_or_404(reservation.user_id)
    spot = reservation.spot  # Using the relationship

    if request.method == "POST":
        # Seting leaving time
        reservation.leaving_timestamp = datetime.utcnow()
        # Calculate duration in minutes
        duration_minutes = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 60
        # Calculate cost (rate is per minute/hour )
        total_cost = round(duration_minutes * reservation.parking_cost_per_unit, 2)

        # Create payment record
        payment_method = request.form.get("payment_method")
        payment = Payment(
            reservation_id=reservation.id,
            amount=total_cost,
            payment_method=payment_method,
            status='Success',  # can  handle failures later
            timestamp=datetime.utcnow()  #record when you pay
        )
        db.session.add(payment)
        # Updating spot status to Available when releases
        spot.status = 'A'
        db.session.commit() #saving the changes
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



#other supported functions
def get_parkingspot(id):
    parkingspot=ParkingSpot.query.filter_by(id=id).first()
    return parkingspot

def get_parkinglot(id):
    parkinglot=ParkingLot.query.filter_by(id=id).first()
    return parkinglot

def get_user_by_email(email):
    return UserInfo.query.filter_by(email=email).first()

def get_parking_lot_by_id(lot_id):
    return ParkingLot.query.get(lot_id)