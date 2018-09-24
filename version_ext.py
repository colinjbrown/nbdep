class ImportWatcher(object):
    def __init__(self,ip):
        import sys
        import logging
        self.sys = sys
        self.shell = ip
        self.modules = self.get_top_levels(list(sys.modules))
        self.logger = logging.getLogger()

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
        for mod in incoming:
            imported = __import__(mod)
            try:
                v = imported.__version__
            except AttributeError:
                v = "Unknown"
            #20 corresponds to an INFO log which would be more ideal
            #but we'd have to modify IPython config to do so
            self.logger.log(30,"Package: "+mod+" Version: "+v)


def load_ipython_extension(ip):
    iw = ImportWatcher(ip)
    ip.events.register('post_execute', iw.grab_modules)


# Can do something with unload here later on
# def unload_ipython_extension(ipython):
