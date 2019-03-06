def load(conda_flag,conda_channels):
    import pymongo
    versions = None
    conda = []
    try:
        client = pymongo.MongoClient("mongodb://public1:public1@ds145848.mlab.com:45848/pypi_mod_index",serverSelectionTimeoutMS=5000)
        client.server_info()
        mongo_flag = True
        db = client["pypi_mod_index"]
        top = db['modules']
        subs = db['submodules']
        v_client = pymongo.MongoClient("mongodb://public1:public1@ds153314.mlab.com:53314/pypi3",serverSelectionTimeoutMS=5000)
        v_db = v_client["pypi3"]
        versions = v_db['versions']
        if conda_flag:
            conda_client = pymongo.MongoClient("mongodb://public1:public1@ds135760.mlab.com:35760/os_pypi_conda",
                                           serverSelectionTimeoutMS=5000)
            conda_db = conda_client['os_pypi_conda']
            for channel in conda_channels:
                conda.append(conda_db['conda-'+channel])
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
    return top,subs,mongo_flag,versions,conda