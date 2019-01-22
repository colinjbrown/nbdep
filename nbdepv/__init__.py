#Colin Brown 2018
#Ipython Magic portion of NBDepv

def _jupyter_server_extension_paths():
    """Magically-named function for jupyter extension installations."""
    return []

def _jupyter_nbextension_paths():
    """Required to load JS button"""
    return [dict(
        section="notebook",
        src="static",
        dest="nbdepv",
        require="nbdepv/index")]

class ImportWatcher(object):
    def __init__(self,ip):
        import sys
        import logging
        self.comm = None
        self.sys = sys
        self.shell = ip
        self.modules = list(sys.modules) #self.get_top_levels(list(sys.modules))
        self.logger = logging.getLogger()
        self.debug = False

    #No longer rely on this method since we export more than just top levels now
    # @staticmethod
    # def get_top_levels(modules):
    #     top_levels = set()
    #     for mod in modules:
    #         top_levels.add(mod.split('.')[0])
    #     return top_levels

    def grab_modules(self):
        if self.comm == None:
            from ipykernel.comm import Comm
            self.comm = Comm(target_name='nbdepv', data={})
        new_mods = list(self.sys.modules) #self.get_top_levels(list(self.sys.modules))
        incoming = set(new_mods) - set(self.modules)
        self.modules = new_mods
        metadata = {}
        for mod in incoming:
            try:
                imported = self.sys.modules[mod]
                #imported = __import__(mod)
                try:
                    v = imported.__version__
                #Does not have a valid version number
                except AttributeError:
                    v = "Unknown"
                    if '.' in mod:
                        top_level = mod.rsplit('.',1)[0]
                        if top_level in metadata:
                            v = metadata[top_level]
                        else:
                            try:
                                top_level = mod.split('.')[0]
                                v = self.sys.modules[top_level].__version__
                            #Triggers both when the top level isn't imported
                            #and if __version__ isn't valid on the top level library
                            except AttributeError:
                                pass
            #Unknown key, shouldn't happen, but we'd rather catch this
            except AttributeError:
                v = "Unknown"
            metadata[mod] = v
            if self.debug:
                self.logger.log(30,"Package: "+mod+" Version: "+v)
        self.comm.send(metadata)

def load_ipython_extension(ip):
    iw = ImportWatcher(ip)
    ip.events.register('post_execute', iw.grab_modules)

def _jupyter_bundlerextension_paths():
    """Declare bundler extensions provided by this package."""
    return [
    {
        # unique bundler name
        "name": "reqs-export",
        # module containing bundle function
        "module_name": "nbdepv.pip_export",
        # human-redable menu item label
        "label": "Produce requirements.txt",
        # group under 'deploy' or 'download' menu
        "group": "deploy",
    }
    ]
# Can do something with unload here later on
# def unload_ipython_extension(ipython):
