
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class Player (GObject):
    __gsignals__ = {'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ())}
    
    def __init__(self):
        GObject.__init__(self)
        self.player = gst.element_factory_make("playbin")
        self.player.get_bus().add_watch(self.on_message)
    
    def on_message(self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            gsterror, message = message.parse_error()
            print message
        elif message.type == gst.MESSAGE_EOS:
            self.emit("end")
        return True
    
    def play(self, uri):
        self.player.set_state(gst.STATE_NULL)
        self.player.set_property("uri", uri)
        self.player.set_state(gst.STATE_PLAYING)

def playSound (uri):
    ensureReady ()
    lock.acquire()
    try:
        player.play(uri)
    finally:
        lock.release()

ready = False
def ensureReady ():
    global ready
    if ready:
        return
    else: ready = True
    
    import pygst
    pygst.require('0.10')
    global player, lock, gst
    import gst
    player = Player()
    from threading import Lock
    lock = Lock()
    
