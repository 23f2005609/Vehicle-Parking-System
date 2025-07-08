from flask import  render_template, request, url_for, redirect, flash
from models.models import *
from flask import current_app as app


@app.route("/")
def home_page():
    return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def user_signin():
    if request.method=="POST":
        #it retirives form values from login form
        u_name=request.form.get("user_name") 
        pwd=request.form.get("password")
        usr=UserInfo.query.filter_by(email=u_name,password=pwd).first() #it matches values from form does it exists or not
        if usr and usr.id==1: #Existed and the first registerd will be the admin that we will auto create
            return redirect(url_for("admin_dash",email=u_name))
        elif usr:
            return redirect(url_for("user_dash",email=u_name))
        else:
            flash("Incorrect User Details!, try again..", "danger")
            return redirect(url_for("user_signin"))
        
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"]) #GET- while showing form and POST- while submiting form
def user_signup():
    if request.method=="POST":
        #gets input from registration form
        u_name=request.form.get("user_name")
        pwd=request.form.get("password")
        fullname=request.form.get("fullname")
        phn=request.form.get("phn_no")
        address=request.form.get("address")
        pin=request.form.get("pin_code")
        usr=UserInfo.query.filter_by(email=u_name,password=pwd).first() # we are checking if user already exists or not
        if usr:
            flash("This email is already registered, try login now!", "danger")
            return redirect(url_for("user_signin"))
        #creates new userinfo and saves it to db
        new_usr=UserInfo(email=u_name,password=pwd,fullname=fullname,phone=phn,address=address,pin_code=pin)
        db.session.add(new_usr)
        db.session.commit()
        flash("Registration is Successfull, lets login!", "success")
        return redirect(url_for("user_signin"))
    return render_template("signup.html")

