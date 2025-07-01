# Starting of the app
from flask import Flask
from models.models import db, UserInfo
from controllers.api_controllers import api  

# Automatically Creates admin without registration
def create_admin():
    admin_email = "admin@gmail.com"
    existing_admin = UserInfo.query.filter_by(email=admin_email).first()
    
    if not existing_admin:
        admin = UserInfo(
            fullname="Admin",
            email=admin_email,
            password="admin1",  
            address="Dhaleswar, Kalyani",
            pin_code="799007"
        )
        db.session.add(admin)
        db.session.commit()
    

def setup_app():
    app=Flask(__name__)
    app.secret_key = 'super_secret_@123'  # You can use any random string here , we need this if we use flask sessions , flash

    app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///vehicle_parking.sqlite3" #Having db file

    db.init_app(app) #Flask app connected to db(SQL alchemy)
    with app.app_context():
        db.create_all()   #creates db if not there
        create_admin()   #auto creates admin

    api.init_app(app) #Flask App connect to Apis
    app.app_context().push() #Direct access to other modules
    app.debug=True
    print("Vehicle app is running...")
    return app

#Call the setup
app=setup_app()

from controllers.auth_controller import *
from controllers.admin_controller import *
from controllers.user_controller import *
from controllers.parkinglot_controller import *

if __name__=="__main__":
    app.run(debug=True)

