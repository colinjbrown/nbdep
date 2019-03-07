import os
from stdlib_list import stdlib_list
from nbdepv.load_data import load
from collections import defaultdict
#import requests
from platform import system
import sys
import re

#Setting this flag to false will stop the use of conda channels entirely
conda = True
#This will prioritize the main channel followed by the forge channel and then followed by the free channel
conda_channel_names = ['main','forge','free']

#This is a maintained blacklist for package names that used to be their own packages but now are part of another package
#Anyone who wants to install mkl-fft seperately from pypi should do so but the conda equivalent is preferred
blacklist = ['mtrand','mkl-fft']

#Translates names of certain packages that are maintained only as aliases in other packages
#IE if you try and import py.test it will actually load the pytest module into sys.modules as py.test
translate_list = {'py.test':'pytest'}

# Taken from https://github.com/python/cpython/commit/7d81e8f5995df6980a1a02923e224a481375f130
# See https://bugs.python.org/issue14894

# Helper for comparing two version number strings.
# Based on the description of the PHP's version_compare():
# http://php.net/manual/en/function.version-compare.php

_ver_stages = {
    # any string not found in this dict, will get 0 assigned
    'dev': 10,
    'alpha': 20, 'a': 20,
    'beta': 30, 'b': 30,
    'c': 40,
    'RC': 50, 'rc': 50,
    # number, will get 100 assigned
    'pl': 200, 'p': 200,
}

_component_re = re.compile(r'([0-9]+|[._+-])')


def _comparable_version(version):
    result = []
    for v in _component_re.split(version):
        if v not in '._+-':
            try:
                v = int(v, 10)
                t = 100
            except ValueError:
                t = _ver_stages.get(v, 0)
            result.extend((t, v))
    return result


top,subs,mongo_flag,versions,conda_channels = load(conda,conda_channel_names)
deps = {}

def export_reqs(file,fname):
    pip_reqs = {}

    py_version = '.'.join(file['metadata']['language_info']['version'].split('.')[:2])
    libraries = stdlib_list(py_version)

    def add_pip(dep, version):
        #We always want the lower version as our upper limit
        if dep in pip_reqs:
            # If we don't know a version then we just use Unknown as a placeholder
            if pip_reqs[dep] == 'Unknown' or _comparable_version(pip_reqs[dep]) > _comparable_version(version):
                pip_reqs[dep] = version
        else:
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
                process_obj(top, 'module', dep.split('.')[0], version, False)
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
                    process_mongo(top, 'module', top_level, version, False)
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
                if _comparable_version(deps[dep]) < _comparable_version(session['deps'][dep]):
                    deps[dep] = session['deps'][dep]
            else:
                deps[dep] = session['deps'][dep]

    if mongo_flag:
        top_levels = []
        submods = []
        #Seperate these so we can do a single query
        for dep in deps:
            if dep in translate_list:
                dep = translate_list[dep]
            if dep.count('.') == 0:
                top_levels.append(dep)
            elif dep.count('.') == 1:
                submods.append(dep)
        for top_level in top.find({'module':{'$in':top_levels}}):
            dep = top_level['module']
            version = deps[dep]
            packages = top_level['packages']
            valid_candidates = [k['package'] for k in packages if version in k['versions']]
            process_mongo_new(dep,version,valid_candidates,packages)
        completed_submods = []
        for submod in subs.find({'submodule':{'$in':submods}}):
            dep = submod['submodule']
            version = deps[dep]
            packages = submod['packages']
            valid_candidates = [k['package'] for k in packages if version in k['versions']]
            process_mongo_new(dep,version,valid_candidates,packages)
            completed_submods.append(dep)
        #No reason to query the same things twice, but if we can't find a submodule we should try querying it's top level module
        final_top_set = [i for i in [i.split('.')[0] for i in set(submods) - set(completed_submods)] if i not in top_levels]
        for top_level in top.find({'module':{'$in':final_top_set}}):
            dep = top_level['module']
            version = deps[dep]
            packages = top_level['packages']
            valid_candidates = [k['package'] for k in packages if version in k['versions']]
            process_mongo_new(dep,version,valid_candidates,packages)
    else:
        for dep, version in deps.items():
            if dep in translate_list:
                dep = translate_list[dep]
            if dep.count('.') == 0:
                if mongo_flag:
                    process_mongo(top,'module',dep, version, False)
                else:
                    process_obj(top, 'module', dep, version, False)
            elif dep.count('.') == 1:
                if mongo_flag:
                    process_mongo(subs,'submodule',dep,version,False)
                else:
                    process_obj(subs, 'submodule', dep, version, True)

    for key in list(pip_reqs):
        if key in blacklist:
            pip_reqs.pop(key)

    os_mapping = {'Darwin': 'OSX', 'Windows': 'Win', 'Linux': 'Linux', 'ppc64le': 'Linuxppc'}
    os_mapping = defaultdict(lambda: 'NoArchNA', os_mapping)

    os_key = os_mapping[system()]

    if os_key != 'NoArchNA':
        os_key += '64' if sys.maxsize > 2 ** 32 else '32'

    conda_packages = defaultdict(list)

    for channel,channel_name in zip(conda_channels,conda_channel_names):
        for c_package in channel.find({'package':{'$in':list(pip_reqs.keys())}}):
            if pip_reqs[c_package['package']] in c_package[os_key]:
                conda_packages[channel_name].append(c_package['package']+'='+pip_reqs.pop(c_package['package']))

    if conda_packages:
        with open('environment.yml','w') as f:
            f.write('#Operating System produced under:'+os_key+'\n')
            f.write('name: '+fname[:-len('.ipynb')]+'\n')
            channel_flag = False
            for key in conda_packages:
                if key in ['main','free']:
                    continue
                if not channel_flag:
                    f.write('channels:\n')
            f.write('dependencies:\n')
            f.write('  - python='+py_version+'\n')
            for k,v in conda_packages.items():
                for dep in v:
                    f.write('  - '+dep+'\n')
            if versions != None and len(pip_reqs) > 0:
                #Have to convert to a list otherwise will throw a bson error
                #Need to only write in the case that there are valid versions
                pip_write = False
                for version in versions.aggregate([{'$match':{'package':{'$in':list(pip_reqs.keys())}}},{'$unwind':'$versions'},{'$group':{'_id':'$package','versions':{'$addToSet':'$versions.version'}}}]):
                    #Mongo has some weird requirement for aggregation objects so we use _id
                    package = version['_id']
                    if package in libraries:
                        continue
                    if not pip_write:
                        f.write('  - pip:\n')
                    if pip_reqs[package] in version['versions']:
                        f.write('    - '+package + '==' + pip_reqs[package] + '\n')
                    else:
                        f.write('    - '+package + '\n')
        dir_name, _ = os.path.split(os.path.abspath(fname))
        return os.path.join(dir_name, 'environment.yml')
    else:
        #Validate everything on the backend with pypi
        with open('requirements.txt', 'w') as f:
            if versions != None:
                #Have to convert to a list otherwise will throw a bson error
                for version in versions.aggregate([{'$match':{'package':{'$in':list(pip_reqs.keys())}}},{'$unwind':'$versions'},{'$group':{'_id':'$package','versions':{'$addToSet':'$versions.version'}}}]):
                    #Mongo has some weird requirement for aggregation objects so we use _id
                    package = version['_id']
                    if package in libraries:
                        continue
                    if pip_reqs[package] in version['versions']:
                        f.write(package + '==' + pip_reqs[package] + '\n')
                    else:
                        f.write(package + '\n')
            # else:
            #     for k, v in pip_reqs.items():
            #         if v == 'Unknown':
            #             r = requests.head("https://pypi.org/pypi/{}/json"
            #                                      .format(k))
            #             if r.status_code == 200:
            #                 f.write(k + '\n')
            #         else:
            #             r = requests.head("https://pypi.org/pypi/{}/{}/json"
            #                                      .format(k, v))
            #             if r.status_code == 200:
            #                 f.write(k + '==' + v + '\n')
            #             else:
            #                 r = requests.head("https://pypi.org/pypi/{}/json"
            #                                          .format(k))
            #                 if r.status_code == 200:
            #                     f.write(k + '\n')
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