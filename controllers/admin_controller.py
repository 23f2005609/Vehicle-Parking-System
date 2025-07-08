from flask import  render_template, request, url_for, redirect, flash, jsonify
from models.models import *
from flask import current_app as app
import os
import matplotlib
matplotlib.use('Agg')  #  Prevents GUI/thread errors
import matplotlib.pyplot as plt


#Common route for admin dashbaord
@app.route("/admin/<email>")
def admin_dash(email):
    admin = UserInfo.query.filter_by(email=email).first()
    parkinglots = get_lots() #using helper function to get parking lots
    parkinglots = cal_avail_spots(parkinglots) #Using helper function to compute available spots

    return render_template("admin_dash.html", email=email, parkinglots=parkinglots, user=admin,is_search=False) #we are just viewing not searching
@app.route("/admin_search/<email>", methods=["GET", "POST"])
def admin_search(email):
    admin = UserInfo.query.filter_by(email=email).first() # fetching by email in url and first returns single object or none
    if request.method == "POST":
        s_txt = request.form.get("s_txt") #text admin enters in form to search
        s_type = request.form.get("s_type") #type admin selects in select form in html

        # validating if admin has searched something or not
        if not s_txt or not s_type:
            flash("Please enter something and select a search type!", "danger")
            return redirect(url_for("admin_dash", email=email))

        if s_type == "user_id":
            parkinglots = find_by_user_id(s_txt)
        elif s_type == "address":
            parkinglots = find_by_address(s_txt)
        elif s_type == "pin_code":
            parkinglots = find_by_pincode(s_txt)
        else:
            parkinglots = [] #Returns empty if not found

        if parkinglots:
            parkinglots = cal_avail_spots(parkinglots)  #if parking lot found it updates with avail spots by calling helper function

        return render_template("admin_dash.html", user=admin, email=email, parkinglots=parkinglots, s_txt=s_txt,is_search=True) #when we are searching
    return redirect(url_for("admin_dash", email=email))


@app.route("/edit_admin_profile/<id>/<email>", methods=["GET","POST"])
def update_admin_profile(id,email):
    A=UserInfo.query.get(id)  #gets id from userinfo
    if request.method=="POST":
        # gets the data admin enterd in form HTML
        Email=request.form.get("email")
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        phn=request.form.get("phn_no")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
         # updates db with new records
        A.email=Email
        A.password=Password
        A.fullname=Fullname
        A.phone=phn
        A.address=Address
        A.pin_code=Pin_code
        db.session.commit() #commits data permanently in db
        flash(f"{A.fullname}'s Profile Updated Successfully!", "success")
        return redirect(url_for("admin_dash",email=A.email))
     
    return render_template("edit_admin_profile.html",user=A,email=email)

#route to see all the registered users by admin
@app.route('/users/<email>')
def all_registered_users(email):
    admin = UserInfo.query.filter_by(email=email).first()
    users = UserInfo.query.filter(UserInfo.email != "admin@gmail.com").all() #show all the users except admin
    return render_template('reg_users.html', users=users, user=admin, email=email)

@app.route('/admin/summary/<email>')
def summary_admin(email):
    admin = UserInfo.query.filter_by(email=email).first()  #fetch admin by email
    parkinglots = ParkingLot.query.all() #fetch all parking lots
    payments = Payment.query.all()
    total_amount = sum(payment.amount or 0 for payment in payments)
    total_lots = len(parkinglots)
    lot_labels = []
    revenues = []
    for lot in parkinglots:
        #for each lot get all its spots
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        total_revenue = 0
        for s in spots:
            #for each spot get the reservation
            reservations = ReserveParkingSpot.query.filter_by(spot_id=s.id).all()
            for r in reservations:
                total_revenue += r.parking_cost_per_unit or 0
        lot_labels.append(lot.prime_location_name)
        revenues.append(total_revenue)
    
    plt.figure(figsize=(6, 4))
    plt.title("Total ₹ Revenue Per Parking Lot")
    if revenues and any(r > 0 for r in revenues):
        plt.pie(
            revenues, 
            labels=lot_labels, 
            autopct='%1.1f%%', 
            startangle=140, 
            shadow=True
        )
        plt.axis('equal')  #it Keeps pie circular
        pie_path = os.path.join('static', 'Revenue_pie_chart.png')
        plt.savefig(pie_path)
        plt.tight_layout()
        plt.close()
    else: #if no data available no revenue yet
        plt.text(0.5, 0.5, "No Data Available !", ha='center', va='center', fontsize=18, color='red')
        plt.axis('off')
        pie_path = os.path.join('static', 'Revenue_pie_chart.png')
        plt.savefig(pie_path)
        plt.close()
    
    # --- 2. Occupied vs Available Bar Chart ---
    occupied_nos = []
    available_nos = []
    lot_labels = []
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        occupied = sum(1 for spot in spots if spot.status == 'O') #count how many spots are occupied and available
        available = sum(1 for spot in spots if spot.status == 'A')
        occupied_nos.append(occupied)
        available_nos.append(available)
        lot_labels.append(lot.prime_location_name)
    x = range(len(lot_labels))
    plt.figure(figsize=(6, 4))
    plt.title("Available vs Occupied Bar Chart")
    plt.bar(x, available_nos, width=0.4, label='Available', color='green')
    plt.bar([i + 0.4 for i in x], occupied_nos, width=0.4, label='Occupied', color='red')
    #shifts the "Occupied" bars slightly to the right of the "Available" bars so they don’t get overlap
    wrap_labels = [label.replace(" ", "\n") for label in lot_labels]
    plt.xticks([i + 0.2 for i in x], wrap_labels, rotation=0,ha='right') #ha='center': aligns text in center in multiline label under bar
    plt.legend()
    plt.tight_layout(pad=2.0)
    bar_path = os.path.join('static', 'Occupied_available_bar_chart.png')
    plt.savefig(bar_path)
    plt.close()

    return render_template('admin_summary.html',email=email,parkinglots=parkinglots,user=admin,total_amount=total_amount,total_lots=total_lots)


@app.route("/parkinglot/<email>", methods=["POST","GET"]) #GET:to display lot form and POST:to process submitted data
def add_parking_lot(email):
    admin = UserInfo.query.filter_by(email=email).first()
    if request.method=="POST": #runs when admin submits or its a POST request
        # Checking if request is JSON API 
        if request.is_json:
            #extracts data from json API 
            data = request.get_json()
            pname = data.get('prime_location_name')
            address = data.get('address')
            pin_code = data.get('pin_code')
            price = float(data.get('price'))
            max_spots = int(data.get('maximum_number_of_spots'))
        else:
            # if it is not json api extract data from html form
            pname=request.form.get('prime_location_name')  
            address=request.form.get('address')
            pin_code=request.form.get('pin_code')
            price=request.form.get('price')
            max_spots=int(request.form.get('maximum_number_of_spots'))
        #LHS attribute name in db, RHS is data fetched from form
        new_parkinglot=ParkingLot(prime_location_name=pname,address=address,pin_code=pin_code,price=price,maximum_number_of_spots=max_spots)    
        db.session.add(new_parkinglot)
        db.session.commit()
        # Auto-creates new parking spots based on maximum spots
        for _ in range(max_spots):
            new_spot = ParkingSpot(lot_id=new_parkinglot.id, status='A') 
            db.session.add(new_spot)
        db.session.commit()

        # it will return JSON if API, or redirect if form
        if request.is_json:
            return jsonify({
                "message": "Parking lot and spots created",
                "lot_id": new_parkinglot.id,
                "spots_created": max_spots
            }), 201
        else:
            flash("New Parking Lot Created Succesfully!", "success")
            return redirect(url_for("admin_dash",email=email))

    return render_template("AddLot.html",email=email,user=admin)

@app.route("/edit_lot/<id>/<email>", methods=["GET","POST"])
def update_parkinglot(id,email):
    L=get_parkinglot(id) #gets parking lot by id
    admin = UserInfo.query.filter_by(email=email).first()
    if request.method=="POST":
        # it retrives value from form 
        location=request.form.get("prime_location_name")
        address=request.form.get("address")
        pincode=request.form.get("pincode")
        price=request.form.get("price")
        new_max_spots=int(request.form.get("maximum_number_of_spots"))
        #it counts current no. of spots
        current_spot_count = ParkingSpot.query.filter_by(lot_id=id).count()
        # updates lot with new values
        L.prime_location_name=location
        L.address=address
        L.pincode=pincode
        L.price=price
        L.maximum_number_of_spots=new_max_spots
        db.session.commit()

        # If thenew spot count is greater than old, add new spots, happens if admin increases no of spots 
        if new_max_spots > current_spot_count:
            for _ in range(new_max_spots - current_spot_count):
                new_spot = ParkingSpot(lot_id=id, status='A')
                db.session.add(new_spot)
            db.session.commit()
        # If the new spot count is less than old, it deletes excess spots
        elif new_max_spots < current_spot_count:
            # Cal how many spots need to be removed
            spots_to_remove = current_spot_count - new_max_spots
            # Fetch only the available spots ordered by most recently created
            removable_spots = ParkingSpot.query.filter_by(lot_id=id, status='A').order_by(ParkingSpot.id.desc()).limit(spots_to_remove).all()
            #while editing if the no. of available spots is less than the no. of spots to be removed
            if len(removable_spots) < spots_to_remove: 
                flash("Can't reduce spots anymore!, not enough available spots to remove", "danger")
                return redirect(url_for('update_parkinglot', id=id, email=email))
            for spot in removable_spots:
                db.session.delete(spot) #delete the spot
            db.session.commit()

        flash("Parking Lot is Updated Successfully !", "success")
        return redirect(url_for("admin_dash",email=email))
     
    return render_template("edit_lot.html",parkinglot=L,email=email,user=admin)


@app.route("/delete_parkinglot/<int:id>/<email>", methods=["POST"])
def delete_parkinglot(id, email):
    parkinglot = ParkingLot.query.get(id) #gets parking lot by id
    occupied_spots = ParkingSpot.query.filter_by(lot_id=id, status='O').count() #counts the occupied spots in lot
    # Don't delete lot if any spot even if one spot is occupied
    if occupied_spots > 0:
        flash("Can't delete parking lot, Some parking spots are still occupied!", "danger")
        return redirect(url_for("admin_dash", email=email))
    
    
    # it deletes all related payments when lot is deleted
    reservations = ReserveParkingSpot.query.filter_by(lot_id=id).all()
    for r in reservations:
        Payment.query.filter_by(reservation_id=r.id).delete()
    # it deletes all related reservations when lot is deleted
    ReserveParkingSpot.query.filter_by(lot_id=id).delete()
    # it deleted allrelated spots when lot is deleted
    ParkingSpot.query.filter_by(lot_id=id).delete()
    db.session.delete(parkinglot)
    db.session.commit()
    flash("Parking Lot Deleted Successfully !", "success")
    return redirect(url_for("admin_dash", email=email))


@app.route("/spot/<int:spot_id>/<email>")
def view_parkingspot(spot_id,email):
    spot = ParkingSpot.query.get(spot_id) # it gets parking spot by id
    #  Only fetching  active reservation that is not yet released)
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
    # We are updating spot status base on reservation
    spot.status = 'O' if reservation else 'A'

    return render_template("view_spot.html", spot=spot, reservation=reservation,email=email)

@app.route("/delete_spot/<int:spot_id>/<email>")
def delete_parkingspot(spot_id,email):
    spot = ParkingSpot.query.get(spot_id) # it gets spot by id
    if spot.status == 'O':  #do not delete if it is occupied
        flash("Soory, Can't delete occupied spot!", "danger")
        return redirect(url_for('view_parkingspot', spot_id=spot.id, email=email))
    db.session.delete(spot)
    db.session.commit()
    flash("Parking Spot Deleted Successfully !", "success")
    return redirect(url_for('admin_dash', email=email))  


@app.route("/occupied_details/<int:spot_id>/<email>")
def occupied_info(spot_id,email):
    spot = ParkingSpot.query.get(spot_id)
    # it gets the latest reservation for the spot
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot_id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
    if not reservation:
        return redirect(url_for('view_spot', spot_id=spot_id, email=email))

    return render_template("occupied_details.html", spot=spot, reservation=reservation, email=email)


#route to see all payments of users by admin
@app.route('/admin/payments/<email>')
def all_payment(email):
    user = UserInfo.query.filter_by(email=email).first()
    payments = Payment.query.order_by(Payment.timestamp.desc()).all() #gets all the latest payment records
    return render_template('admin_pay.html', payments=payments, user=user,email=email)

# Helper Functions 
def get_lots():
    parkinglots = ParkingLot.query.all()
    for lot in parkinglots:
        # Get all spots for this lot
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        # Count how many are available
        available = sum(1 for s in spots if s.status == 'A')
        # Add this info dynamically
        lot.available_spots = available
    return parkinglots


def cal_avail_spots(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all() #fetching all the spots in the lot
        available_count = 0
        occupied_count = 0
        for spot in spots: #Looping through each spot
            #Checking if the spot is reserved or not, if leaving timestamp is None it means user has not released yet
            active_reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
            if active_reservation:
                spot.status = 'O'
                occupied_count += 1
            else:
                spot.status = 'A'
                available_count += 1
            db.session.add(spot)  #updating spot status in db
        #updating in parking lots with current counts
        lot.available_count = available_count 
        lot.occupied_count = occupied_count
    db.session.commit() #saving all spot status
    return parkinglots


def find_by_user_id(s_txt):
    user_id=ParkingLot.query.filter(ParkingLot.id.ilike(f"%{s_txt}%")).all() #returns all id searched by user or admin, ilike matches the searched input
    return user_id

def find_by_address(s_txt):
    location=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{s_txt}%")).all() #returns all address searched by user or admin
    return location

def find_by_pincode(s_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{s_txt}%")).all()  #returns all pincode searched by user or admin
    return pin_code

def get_parkinglot(id):
    parkinglot=ParkingLot.query.filter_by(id=id).first()
    return parkinglot


def mark_spot_status(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        for spot in spots:
            # reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).first()
            reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
            spot.status = 'O' if reservation else 'A'
        lot.parkingspot = spots  # this is key
    return parkinglots
