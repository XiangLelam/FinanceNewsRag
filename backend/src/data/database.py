import pymongo
import src.config.constant as cons
from bson import ObjectId   

def connect_db():
    client = pymongo.MongoClient(cons.HOST)
    db = client[cons.DATABASE]
    collection = db[cons.COLLECTION]
    return collection

def save_data(data,collection):
    collection.insert_one(data)

def load_data(collection,id):
    data = collection.find_one({"_id": ObjectId(id)})
    return data
def load_all_data(collection):
    data = collection.find()
    return data