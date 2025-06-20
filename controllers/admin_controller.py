from flask import Flask, render_template, request, url_for, redirect
from models.models import *
from flask import current_app as app
import os
import matplotlib
matplotlib.use('Agg')  # Use Anti-Grain Geometry backend (no GUI)
import matplotlib.pyplot as plt
from io import BytesIO


#Common route for admin dashbaord
@app.route("/admin/<email>")
def admin_dashboard(email):
    user = UserInfo.query.filter_by(email=email).first()
    parkinglots = get_parkinglots()
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        available_count = 0
        occupied_count = 0
        for spot in spots:
            # Check if this spot has an active reservation or not
            active_reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
            if active_reservation:
                spot.status = 'O'
                occupied_count += 1
            else:
                spot.status = 'A'
                available_count += 1
            # update spot status in DB
            db.session.add(spot)
        # Update lot with latest counts
        lot.available_count = available_count
        lot.occupied_count = occupied_count

    db.session.commit()  # Save all spot status updates

    return render_template("admin_dash.html", email=email, parkinglots=parkinglots, user=user)


@app.route("/search/<email>", methods=["GET","POST"])
def search(email):
    if request.method=="POST":
        search_txt=request.form.get("search_txt")
        by_lot=search_by_user_id(search_txt)
        by_location=search_by_location(search_txt)
        by_pincode=search_by_pincode(search_txt)
        user = UserInfo.query.filter_by(email=email).first()

        if by_lot:
            return render_template("admin_dash.html",email=email,parkinglots=by_lot, user=user,is_search=True)
        elif by_location:
            return render_template("admin_dash.html",email=email,parkinglots=by_location,user=user,is_search=True)
        elif by_pincode:
            return render_template("admin_dash.html",email=email,parkinglots=by_pincode,user=user,is_search=True)
        # Return empty list if no match found
        return render_template("admin_dash.html", email=email,user=user, parkinglots=[],is_search=True)


    return redirect(url_for("admin_dashboard",email=email))

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



@app.route("/edit_admin_profile/<id>/<email>", methods=["GET","POST"])
def edit_admin_profile(id,email):
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
        return redirect(url_for("admin_dashboard",email=E.email))
     
    return render_template("edit_admin_profile.html",user=E,email=email)

@app.route('/users/<email>')
def registered_users(email):
    user = UserInfo.query.filter_by(email=email).first()
    users = UserInfo.query.filter(UserInfo.email != "admin@gmail.com").all()
    return render_template('users.html', users=users, user=user, email=email)

@app.route('/admin/summary/<email>')
def admin_summary(email):
    parkinglots = ParkingLot.query.all()
    user = UserInfo.query.filter_by(email=email).first() 
    
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
    
    plt.figure(figsize=(6, 5))
    plt.barh(labels, revenues, color='skyblue')
    plt.xlabel("Revenue")
    plt.title("Revenue from Each Parking Lot")
    plt.tight_layout()
    bar_buf = BytesIO()
    plt.savefig(bar_buf, format='png')
    bar_buf.seek(0)
    bar_path = os.path.join('static', 'pie_chart.png')  # reuse the same image path
    with open(bar_path, 'wb') as f:
        f.write(bar_buf.read())
    plt.close()
    # --- 2. Occupied vs Available Bar Chart ---
    occupied_counts = []
    available_counts = []
    labels = []

    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        occupied = sum(1 for spot in spots if spot.status == 'O')
        available = sum(1 for spot in spots if spot.status == 'A')

        occupied_counts.append(occupied)
        available_counts.append(available)
        labels.append(lot.prime_location_name)

    x = range(len(labels))
    plt.figure(figsize=(6, 5))
    plt.bar(x, available_counts, width=0.4, label='Available', color='lightgreen')
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

    return render_template('admin_summary.html',email=email,parkinglots=parkinglots,user=user)

#route to see all payments of users by admin
@app.route('/admin/payments/<email>')
def view_all_payment(email):
    user = UserInfo.query.filter_by(email=email).first()
    payments = Payment.query.order_by(Payment.timestamp.desc()).all()
    return render_template('admin_pay.html', payments=payments, user=user,email=email)


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

def mark_spot_status(parkinglots):
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        for spot in spots:
            # reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).first()
            reservation = ReserveParkingSpot.query.filter_by(spot_id=spot.id).order_by(ReserveParkingSpot.parking_timestamp.desc()).first()
            spot.status = 'O' if reservation else 'A'
        lot.parkingspot = spots  # this is key
    return parkinglots
