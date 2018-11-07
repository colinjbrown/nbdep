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
        from ipykernel.comm import Comm
        self.comm = Comm(target_name='nbdepv', data={})
        self.sys = sys
        self.shell = ip
        self.modules = self.get_top_levels(list(sys.modules))
        self.logger = logging.getLogger()
        self.debug = False

    @staticmethod
    def get_top_levels(modules):
        top_levels = set()
        for mod in modules:
            top_levels.add(mod.split('.')[0])
        return top_levels

    def grab_modules(self):
        new_mods = self.get_top_levels(list(self.sys.modules))
        incoming = set(new_mods) - set(self.modules)
        self.modules = new_mods
        metadata = {}
        for mod in incoming:
            try:
                imported = __import__(mod)
                try:
                    v = imported.__version__
                #Does not have a valid version number
                except AttributeError:
                    v = "Unknown"
            #Not able to be __import__'d
            except ModuleNotFoundError:
                v = "Unknown"
            metadata[mod] = v
            if self.debug:
                self.logger.log(30,"Package: "+mod+" Version: "+v)
        self.comm.send(metadata)

def load_ipython_extension(ip):
    iw = ImportWatcher(ip)
    ip.events.register('post_execute', iw.grab_modules)


# Can do something with unload here later on
# def unload_ipython_extension(ipython):
