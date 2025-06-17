# Vehicle-Parking-System
This is a Flask-based Vehicle Parking Management System for Admins and Users. It includes login, lot and spot management, booking, releasing, and graphical summaries.

Steps To Run the Project:-

1. Clone the Repository
https://github.com/23f2005609/Vehicle_Parking_System.git
cd vehicle_parking_app

2. Install Dependencies

pip install -r requirements.txt

3. Initialize the Database

python
>>> from app import db
>>> db.create_all()
>>> exit()

4. Run the Application

python app.py

The app will be accessible at http://127.0.0.1:5000/
