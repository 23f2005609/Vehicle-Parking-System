from flask import  render_template, request, url_for, redirect, flash
from models.models import *
from flask import current_app as app


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def signin():
    if request.method=="POST":
        #retirives form values from login form
        uname=request.form.get("user_name") 
        pwd=request.form.get("password")
        usr=UserInfo.query.filter_by(email=uname,password=pwd).first() 
        if usr and usr.id==1: #Existed and i am assuming the first registerd will be the admin the users
            return redirect(url_for("admin_dashboard",email=uname))
        elif usr:
            return redirect(url_for("user_dashboard",email=uname))
        else:
            flash("Invalid user credentials...", "danger")
            return redirect(url_for("signin"))
        
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"]) #GET- while showing form and POST- while submiting form
def signup():
    if request.method=="POST":
        #gets input from registration form
        uname=request.form.get("user_name")
        pwd=request.form.get("password")
        fullname=request.form.get("fullname")
        address=request.form.get("address")
        pin=request.form.get("pincode")
        usr=UserInfo.query.filter_by(email=uname,password=pwd).first()
        if usr:
            flash("This email is already registered, try login now!", "danger")
            return redirect(url_for("signin"))
        #creates new userinfo and saves it to db
        new_usr=UserInfo(email=uname,password=pwd,fullname=fullname,address=address,pin_code=pin)
        db.session.add(new_usr)
        db.session.commit()
        flash("Registration Successfull, try login now!", "success")
        return redirect(url_for("signin"))
    return render_template("signup.html")

