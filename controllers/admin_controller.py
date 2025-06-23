from flask import  render_template, request, url_for, redirect
from models.models import *
from flask import current_app as app
import os
import matplotlib
matplotlib.use('Agg')  #  Prevents GUI/thread errors
import matplotlib.pyplot as plt


#Common route for admin dashbaord
@app.route("/admin/<email>")
def admin_dashboard(email):
    user = UserInfo.query.filter_by(email=email).first()
    parkinglots = get_parkinglots() #using helper function to get parking lots
    parkinglots = cal_available_spots(parkinglots) #Using helper function to compute available spots

    return render_template("admin_dash.html", email=email, parkinglots=parkinglots, user=user,is_search=False) #we are just viewing not searching



@app.route("/admin_search/<email>", methods=["GET", "POST"])
def admin_search(email):
    user = UserInfo.query.filter_by(email=email).first() # fetching by email in url and first returns single object or none
    if request.method == "POST":
        search_txt = request.form.get("search_txt") #text admin enters in form to search
        search_type = request.form.get("search_type") #type admin selects in select form in html

        if search_type == "user_id":
            parkinglots = search_by_user_id(search_txt)
        elif search_type == "location":
            parkinglots = search_by_location(search_txt)
        elif search_type == "pin_code":
            parkinglots = search_by_pincode(search_txt)
        else:
            parkinglots = [] #Returns empty if not found

        if parkinglots:
            parkinglots = cal_available_spots(parkinglots)  #if parking lot found it updates with avail spots by calling helper function

        return render_template("admin_dash.html", user=user, email=email, parkinglots=parkinglots, searched_location=search_txt,is_search=True) #when we are searching
    return redirect(url_for("admin_dashboard", email=email))


@app.route("/edit_admin_profile/<id>/<email>", methods=["GET","POST"])
def edit_admin_profile(id,email):
    E=UserInfo.query.get(id)  #gets id from userinfo
    if request.method=="POST":
        # gets the data admin enterd in form HTML
        Email=request.form.get("email")
        Password=request.form.get("password")
        Fullname=request.form.get("fullname")
        Address=request.form.get("address")
        Pin_code=request.form.get("pin_code")
         # updates db with new records
        E.email=Email
        E.password=Password
        E.fullname=Fullname
        E.address=Address
        E.pin_code=Pin_code
        db.session.commit() #commits data permanently in db
        return redirect(url_for("admin_dashboard",email=E.email))
     
    return render_template("edit_admin_profile.html",user=E,email=email)

#route to see all the registered users by admin
@app.route('/users/<email>')
def registered_users(email):
    user = UserInfo.query.filter_by(email=email).first()
    users = UserInfo.query.filter(UserInfo.email != "admin@gmail.com").all()
    return render_template('users.html', users=users, user=user, email=email)

@app.route('/admin/summary/<email>')
def admin_summary(email):
    parkinglots = ParkingLot.query.all() #fetch all parking lots
    user = UserInfo.query.filter_by(email=email).first()  #fetch admin by email
    labels = []
    revenues = []
    for lot in parkinglots:
        #for each lot get all its spots
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        total_revenue = 0
        for spot in spots:
            #for each spot get the reservation
            reservations = ReserveParkingSpot.query.filter_by(spot_id=spot.id).all()
            for res in reservations:
                total_revenue += res.parking_cost_per_unit or 0
        labels.append(lot.prime_location_name)
        revenues.append(total_revenue)
    
    plt.figure(figsize=(6, 5))
    plt.barh(labels, revenues, color='skyblue') #barh is horizontal barchart
    plt.xlabel("Revenue")
    plt.title("Revenue from Each Parking Lot")
    plt.tight_layout()
    bar_path = os.path.join('static', 'Revenue_bar_chart.png')
    plt.savefig(bar_path)
    plt.close()
    # --- 2. Occupied vs Available Bar Chart ---
    occupied_counts = []
    available_counts = []
    labels = []
    for lot in parkinglots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        occupied = sum(1 for spot in spots if spot.status == 'O') #count how many spots are occupied and available
        available = sum(1 for spot in spots if spot.status == 'A')
        occupied_counts.append(occupied)
        available_counts.append(available)
        labels.append(lot.prime_location_name)
    x = range(len(labels))
    plt.figure(figsize=(6, 5))
    plt.bar(x, available_counts, width=0.4, label='Available', color='lightgreen')
    plt.bar([i + 0.4 for i in x], occupied_counts, width=0.4, label='Occupied', color='red')
    #shifts the "Occupied" bars slightly to the right of the "Available" bars so they don’t get overlap
    plt.xticks([i + 0.2 for i in x], labels, rotation=45,ha='right') #ha='right': aligns text so it do not get cut off
    plt.legend()
    plt.title('Occupied vs Available Spots')
    plt.tight_layout(pad=2.0)
    bar_path = os.path.join('static', 'Occupied_available_bar_chart.png')
    plt.savefig(bar_path)
    plt.close()

    return render_template('admin_summary.html',email=email,parkinglots=parkinglots,user=user)

#route to see all payments of users by admin
@app.route('/admin/payments/<email>')
def view_all_payment(email):
    user = UserInfo.query.filter_by(email=email).first()
    payments = Payment.query.order_by(Payment.timestamp.desc()).all() #gets all the latest payment records
    return render_template('admin_pay.html', payments=payments, user=user,email=email)

# Helper Functions 
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


def cal_available_spots(parkinglots):
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


def search_by_user_id(search_txt):
    user_id=ParkingLot.query.filter(ParkingLot.id.ilike(f"%{search_txt}%")).all() #returns all id searched by user or admin, ilike matches the searched input
    return user_id

def search_by_location(search_txt):
    location=ParkingLot.query.filter(ParkingLot.address.ilike(f"%{search_txt}%")).all() #returns all address searched by user or admin
    return location

def search_by_pincode(search_txt):
    pin_code=ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{search_txt}%")).all()  #returns all pincode searched by user or admin
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
