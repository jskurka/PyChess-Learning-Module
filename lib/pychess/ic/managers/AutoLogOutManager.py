from gobject import *
class AutoLogOutManager (GObject):
    __gsignals__ = {
        'logOut': (SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_line (self.onLogOut,
           "\*\*\*\* Auto-logout because you were idle more than \d+ minutes\. \*\*\*\*")
        self.connection.expect_line (self.onLogOut, "Logging you out\.")
        self.connection.expect_line (self.onLogOut,
           "\*\*\*\* .+? has arrived - you can't both be logged in\. \*\*\*\*")
    
    def onLogOut (self, match):
        self.emit("logOut")
