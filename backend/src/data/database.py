import os
from dotenv import load_dotenv
import pymongo
from bson import ObjectId

load_dotenv()

HOST = os.getenv('HOST', 'mongodb://localhost:27017/')
DATABASE = os.getenv('DATABASE')
COLLECTION = os.getenv('COLLECTION')

def connect_db():
    client = pymongo.MongoClient(HOST)
    db = client[DATABASE]
    collection = db[COLLECTION]
    return collection

def save_data(data,collection):
    collection.insert_one(data)

def load_data(collection,id):
    data = collection.find_one({"_id": ObjectId(id)})
    return data

def load_all_data(collection):
    data = collection.find()
    return data