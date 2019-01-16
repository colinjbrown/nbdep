def load():
    import pymongo
    versions = None
    try:
        client = pymongo.MongoClient("mongodb://public1:public1@ds151232.mlab.com:51232/pypi",serverSelectionTimeoutMS=5000)
        client.server_info()
        mongo_flag = True
        db = client["pypi"]
        top = db['top-levels']
        subs = db['submodules']
        v_client = pymongo.MongoClient("mongodb://public1:public1@ds153314.mlab.com:53314/pypi3",serverSelectionTimeoutMS=5000)
        v_db = v_client["pypi3"]
        versions = v_db['versions']
    except pymongo.errors.ServerSelectionTimeoutError:
        #Can't find server
        mongo_flag = False
    if not mongo_flag:
        import os
        import pandas as pd
        top_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(top_path, "./data/top-levels-final.csv")
        top = pd.read_csv(path)
        path = os.path.join(top_path, "./data/submodules-final.csv")
        subs = pd.read_csv(path)
    return top,subs,mongo_flag,versions