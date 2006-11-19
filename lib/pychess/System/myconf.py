try:
    import gconf
    import conf_gconf as confmodule
except:
    import conf_configParser as confmodule

"""Module for using gconf without having to care about types"""

def notify_add (key, func):
    return confmodule.notify_add(key, func)

def get (key):
    return confmodule.get(key)

def set (key, value):
    confmodule.set(key, value)
