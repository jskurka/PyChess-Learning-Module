import re, socket

from gobject import GObject, SIGNAL_RUN_FIRST

from VerboseTelnet import LinePrediction
from VerboseTelnet import ManyLinesPrediction
from VerboseTelnet import FromPlusPrediction
from VerboseTelnet import FromToPrediction
from VerboseTelnet import VerboseTelnet

from managers.GameListManager import GameListManager
from managers.FingerManager import FingerManager
from managers.NewsManager import NewsManager
from managers.BoardManager import BoardManager
from managers.OfferManager import OfferManager
from managers.ChatManager import ChatManager
from managers.ListAndVarManager import ListAndVarManager

from pychess.System.ThreadPool import PooledThread
from pychess.Utils.const import *
from TimeSeal import TimeSeal
from VerboseTelnet import VerboseTelnet, PredictionsTelnet

class LogOnError (StandardError): pass

class Connection (GObject, PooledThread):
    
    __gsignals__ = {
        'connecting':    (SIGNAL_RUN_FIRST, None, ()),
        'connectingMsg': (SIGNAL_RUN_FIRST, None, (str,)),
        'connected':     (SIGNAL_RUN_FIRST, None, ()),
        'disconnecting': (SIGNAL_RUN_FIRST, None, ()),
        'disconnected':  (SIGNAL_RUN_FIRST, None, ()),
        'error':         (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, host, port, username, password):
        GObject.__init__(self)
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        self.connected = False
        self.connecting = False
        
        self.predictions = set()
        self.predictionsDict = {}
    
    def expect (self, prediction):
        self.predictions.add(prediction)
        self.predictionsDict[prediction.callback] = prediction
    
    def unexpect (self, callback):
        self.predictions.remove(self.predictionsDict.pop(callback))
    
    def expect_line (self, callback, regexp):
        self.expect(LinePrediction(callback, regexp))
    
    def expect_many_lines (self, callback, regexp):
        self.expect(ManyLinesPrediction(callback, regexp))
    
    def expect_line_plus (self, callback, regexp):
        def callback_decorator (matchlist):
            callback([matchlist[0]]+[m.group(0) for m in matchlist[1:]])
        self.expect(FromPlusPrediction(callback_decorator, regexp, "\   (.*)"))
    
    def expect_fromplus (self, callback, regexp0, regexp1):
        self.expect(FromPlusPrediction(callback, regexp0, regexp1))
    
    def expect_fromto (self, callback, regexp0, regexp1):
        self.expect(FromToPrediction(callback, regexp0, regexp1))
    
    
    def cancel (self):
        raise NotImplementedError()
    
    def disconnect (self):
        raise NotImplementedError()
    
    def getUsername (self):
        return self.username
    
    def isRegistred (self):
        return self.password
    
    def isConnected (self):
        return self.connected
    
    def isConnecting (self):
        return self.connecting


EOF = _("The connection was broken - got \"end of file\" message")
NOTREG = _("'%s' is not a registered name")
BADPAS = _("The entered password was invalid.\n\n" + \
           "If you have forgot your password, try logging in as a guest and open chat on channel 4. Write \"I've forgotten my password\" to get help.\n\n"+\
           "If that is by some reason not possible, please email: support@freechess.org")

class FICSConnection (Connection):
    def __init__ (self, host, port, username="guest", password=""):
        Connection.__init__(self, host, port, username, password)
        self.registred = None
    
    def _connect (self):
        self.connecting = True
        self.emit("connecting")
        try:
            self.client = VerboseTelnet(TimeSeal())
            
            self.emit('connectingMsg', _("Connecting to server"))
            self.client.open(self.host, self.port)
            
            self.client.read_until("login: ")
            self.emit('connectingMsg', _("Logging on to server"))
            
            if self.username and self.username != "guest":
                print >> self.client, self.username
                got = self.client.read_until("password:",
                                             "enter the server as",
                                             "Try again.")
                if got == 0:
                    self.client.write(self.password)
                    #print >> self.client, self.password
                    self.registred = True
                # No such name
                elif got == 1:
                    raise LogOnError, NOTREG % self.username
                # Bad name
                elif got == 2:
                    raise LogOnError, NOTREG % self.username
            else:
                print >> self.client, "guest"
                self.client.read_until("Press return")
                print >> self.client
                self.registred = False
            
            while True:
                line = self.client.readline()
                if "Invalid password" in line:
                    raise LogOnError, BADPAS
                
                match = re.search("\*\*\*\* Starting FICS session as "+
                                  "([A-Za-z]+)(?:\([A-Z*]+\))* \*\*\*\*", line)
                if match:
                    self.username = match.groups()[0]
                
                if "fics%" in line:
                    break
            
            self.emit('connectingMsg', _("Setting up enviroment"))
            self.client = PredictionsTelnet(self.client)
            self.client.setStripLines(True)
            self.client.setLinePrefix("fics%")
            
            # Important: As the other managers use ListAndVarManager, we need it
            # to be instantiated first. We might decide that the purpose of this
            # manager is different - used by different parts of the code - so it
            # should be implemented into the FICSConnection somehow.
            self.lvm = ListAndVarManager(self)
            while not self.lvm.isReady():
                self.client.handleSomeText(self.predictions)
            self.lvm.setVariable("interface", NAME+" "+VERSION)
            
            # FIXME: Some managers use each other to avoid regexp collapse. To
            # avoid having to init the in a specific order, connect calls should
            # be moved to a "start" function, so all managers would be in
            # the connection object when they are called
            self.glm = GameListManager(self)
            self.bm = BoardManager(self)
            self.fm = FingerManager(self)
            self.nm = NewsManager(self)
            self.om = OfferManager(self)
            self.cm = ChatManager(self)
            
            self.connecting = False
            self.connected = True
            self.emit("connected")
        
        finally:
            self.connecting = False
    
    def run (self):
        try:
            self._connect()
            while self.isConnected():
                self.client.handleSomeText(self.predictions)
        
        except Exception, e:
            if self.connected:
                self.connected = False
            for errortype in (IOError, LogOnError, EOFError,
                              socket.error, socket.gaierror, socket.herror):
                if isinstance(e, errortype):
                    self.emit("error", e)
                    break
            else:
                raise
        
        self.emit("disconnected")
    
    def disconnect (self):
        self.emit("disconnecting")
        if self.isConnected():
            print >> self.client, "quit"
            self.connected = False
        self.client.close()
    
    def isRegistred (self):
        assert self.registred != None
        return self.registred
    
    def getUsername (self):
        assert self.username != None
        return self.username
