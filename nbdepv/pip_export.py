import os
from stdlib_list import stdlib_list
from nbdepv.load_data import load
import requests
from distutils.version import LooseVersion

top,subs,mongo_flag,versions = load()
deps = {}


def export_reqs(file,fname):
    pip_reqs = {}

    py_version = '.'.join(file['metadata']['language_info']['version'].split('.')[:2])
    libraries = stdlib_list(py_version)

    def add_pip(dep, version):
        # pip_reqs.add(dep)
        pip_reqs[dep] = version

    def invalidate_dep(dep,sub_flag):
        if dep.startswith('_'):
            return True
        if not sub_flag:
            if dep in libraries:
                return True
        return False

    def process_obj(df, key, dep, version, sub_flag):
        if invalidate_dep(dep,sub_flag):
            return

        candidates = df[(df[key] == dep)]
        if (len(candidates) == 0):
            if (sub_flag):
                # No candidates try parent module
                process_obj(top, 'top_level_module', dep.split('.')[0], version, False)
                return
            add_pip(dep, version)
        elif (len(candidates) == 1):
            add_pip(candidates['package'].iloc[0], version)
        else:
            get_ver = candidates[candidates.version == version]
            if (len(get_ver) > 1):
                package = get_ver[get_ver.package == dep]
                if len(package) == 1:
                    add_pip(package['package'].iloc[0], version)
                else:
                    add_pip(get_ver['package'].iloc[0], version)
            elif len(get_ver) == 1:
                add_pip(get_ver['package'].iloc[0], version)
            else:
                add_pip(candidates['package'].iloc[0], version)

    def process_mongo_new(dep,version,valid_candidates,packages):
        if valid_candidates:
            if len(valid_candidates) > 1:
                if dep in packages:
                    add_pip(dep, version)
                else:
                    add_pip(valid_candidates[0], version)
            else:
                add_pip(valid_candidates[0], version)
        else:
            add_pip(dep, version)


    def process_mongo(mongo, key, dep, version, sub_flag):
        if invalidate_dep(dep, sub_flag):
            return
        try:
            candidates = mongo.find_one({key:dep},{'packages'})['packages']
        except TypeError:
            #Can't find any packages that match this key
            if (sub_flag):
                # No candidates try parent module
                top_level = dep.split('.')[0]
                if top_level not in deps:
                    process_mongo(top, 'top_level_module', top_level, version, False)
                #return
            #add_pip(dep, version)
            return
        if version == "Unknown":
            add_pip(dep, version)
            return
        else:
            valid_candidates = [k for k in candidates if version in candidates[k]]
            if valid_candidates:
                if len(valid_candidates) > 1:
                    if dep in candidates:
                        add_pip(dep,version)
                    else:
                        add_pip(valid_candidates[0],version)
                else:
                    add_pip(valid_candidates[0],version)
            else:
                add_pip(dep,version)

    for session in file['metadata']['dependencies']:
        for dep in session['deps']:
            if dep in deps:
                if LooseVersion(deps[dep]) < LooseVersion(session['deps'][dep]):
                    deps[dep] = session['deps'][dep]
            else:
                deps[dep] = session['deps'][dep]

    if mongo_flag:
        top_levels = []
        submods = []
        #Seperate these so we can do a single query
        for dep in deps:
            if dep.count('.') == 0:
                top_levels.append(dep)
            elif dep.count('.') == 1:
                submods.append(dep)
        for top_level in top.find({'top_level_module':{'$in':top_levels}}):
            dep = top_level['top_level_module']
            version = deps[dep]
            packages = top_level['packages']
            valid_candidates = [k for k in packages if version in packages[k]]
            process_mongo_new(dep,version,valid_candidates,packages)
        completed_submods = []
        for submod in subs.find({'submodule':{'$in':submods}}):
            dep = submod['submodule']
            version = deps[dep]
            packages = submod['packages']
            valid_candidates = [k for k in packages if version in packages[k]]
            process_mongo_new(dep,version,valid_candidates,packages)
            completed_submods.append(dep)
        #No reason to query the same things twice, but if we can't find a submodule we should try querying it's top level module
        final_top_set = [i for i in [i.split('.')[0] for i in set(submods) - set(completed_submods)] if i not in top_levels]
        for top_level in top.find({'top_level_module':{'$in':final_top_set}}):
            dep = top_level['top_level_module']
            version = deps[dep]
            packages = top_level['packages']
            valid_candidates = [k for k in packages if version in packages[k]]
            process_mongo_new(dep,version,valid_candidates,packages)
    else:
        for dep, version in deps.items():
            if dep.count('.') == 0:
                if mongo_flag:
                    process_mongo(top,'top_level_module',dep, version, False)
                else:
                    process_obj(top, 'top_level_module', dep, version, False)
            elif dep.count('.') == 1:
                if mongo_flag:
                    process_mongo(subs,'submodule',dep,version,False)
                else:
                    process_obj(subs, 'submodule', dep, version, True)

    #Validate everything on the backend with pypi
    with open('requirements.txt', 'w') as f:
        if versions != None:
            #Have to convert to a list otherwise will throw a bson error
            for version in versions.find({'package':{'$in':list(pip_reqs.keys())}}):
                package = version['package']
                if package in libraries:
                    continue
                #TODO: Create a better backend query for this
                v_list = [v['version'] for v in version['versions']]
                if pip_reqs[package] in v_list:
                    f.write(package + '==' + pip_reqs[package] + '\n')
                else:
                    f.write(package + '\n')
        else:
            for k, v in pip_reqs.items():
                if v == 'Unknown':
                    r = requests.head("https://pypi.org/pypi/{}/json"
                                             .format(k))
                    if r.status_code == 200:
                        f.write(k + '\n')
                else:
                    r = requests.head("https://pypi.org/pypi/{}/{}/json"
                                             .format(k, v))
                    if r.status_code == 200:
                        f.write(k + '==' + v + '\n')
                    else:
                        r = requests.head("https://pypi.org/pypi/{}/json"
                                                 .format(k))
                        if r.status_code == 200:
                            f.write(k + '\n')
        dir_name, _ = os.path.split(os.path.abspath(fname))
        return os.path.join(dir_name,'requirements.txt')
    return 'UnexpectedError'


def bundle(handler, model):
    """Creates a requirements.txt file that matches the requirements of this notebook"""
    notebook_filename = model['path']
    notebook_content = model['content']
    import time
    start = time.time()
    handler.finish('File Exported As: {}, Time taken: {}, Mode: {}'.format(export_reqs(notebook_content, notebook_filename),time.time()-start,'Mongo' if mongo_flag else 'Flat File'))

# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: python {} <dfnb filename> [out filename]".format(sys.argv[0]))
#         sys.exit(1)
#
#     out_fname = None
#     if len(sys.argv) > 2:
#         out_fname = sys.argv[2]
#     with open(sys.argv[1], "r") as f:
#         d = json.load(f)
#         export_dfpynb(d, sys.argv[1])