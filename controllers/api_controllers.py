from flask_restful import Resource, Api
from flask import request
from  models.models import *

api=Api() # creating Restful api object

class ParkingLotApi(Resource):
    #Reading of data
    def get(self): # fetching all parking lots
        lots=ParkingLot.query.all()
        Lots_json=[]
        for lot in lots:
            Lots_json.append({'id':lot.id, 'prime_location_name':lot.prime_location_name, 'price':lot.price, 'address':lot.address, 'pin_code':lot.pin_code, 'maximum_number_of_spots':lot.maximum_number_of_spots})
        return Lots_json
    
    #adding new parking lot
    def post(self):
        prime_location_name=request.json.get('prime_location_name')
        price=request.json.get('price')
        address=request.json.get('address')
        pin_code=request.json.get('pin_code')
        max_spots=request.json.get('maximum_number_of_spots')
        new_lot=ParkingLot(prime_location_name=prime_location_name,price=price,address=address,pin_code=pin_code,maximum_number_of_spots=max_spots)
        db.session.add(new_lot)
        db.session.flush()  # we are using flush to get the id of the new lot  without committing nad to ensure lots and spots are saved together
        # it automatically creates parking spots
        for _ in range(int(max_spots)):
            spot = ParkingSpot(lot_id=new_lot.id, status='A')
            db.session.add(spot)
        db.session.commit() # commit the spots

        return {"message":"New lot added!","lot_id": new_lot.id,"spots_created": max_spots}, 201

    #Updating data
    def put(self,id):
        lot=ParkingLot.query.filter_by(id=id).first()
        if lot:
            lot.prime_location_name=request.json.get('prime_location_name')
            lot.price=request.json.get('price')
            lot.address=request.json.get('address')
            lot.pin_code=request.json.get('pin_code')
            lot.max_spots=request.json.get('maximum_number_of_spots')
            db.session.commit()
            return {"message":"Lot Updated"},200
        else:
            return {"message":"Lot not found!"},404

    #Deleting parking lot
    def delete(self,id):
        lot=ParkingLot.query.filter_by(id=id).first()
        if lot:
            db.session.delete(lot)
            db.session.commit()
            return {"message":"Lot Deleted"},200
        else:
            return {"message":"Lot id not found!"},404


#it for search parking lot by its id
class ParkingLotSearchApi(Resource):
    def get(self,id):
        lot=ParkingLot.query.filter_by(id=id).first()
        if lot:
            Lot_json=[]
            Lot_json.append({'id':lot.id, 'prime_location_name':lot.prime_location_name, 'price':lot.price, 'address':lot.address, 'pin_code':lot.pin_code, 'maximum_number_of_spots':lot.maximum_number_of_spots})
            return Lot_json
        else:
            return {"message":"Lot id not found!"},404

api.add_resource(ParkingLotApi,"/api/get_lots","/api/add_lot","/api/edit_lot/<id>","/api/delete_lot/<id>")
api.add_resource(ParkingLotSearchApi,"/api/search_lot/<id>")
