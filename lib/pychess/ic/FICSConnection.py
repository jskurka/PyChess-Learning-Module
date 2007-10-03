import re, socket
from threading import Thread

from gobject import GObject, SIGNAL_RUN_FIRST

from VerboseTelnet import VerboseTelnet, InterruptError

from DisconnectManager import DisconnectManager
from GameListManager import GameListManager
from FingerManager import FingerManager
from NewsManager import NewsManager
from BoardManager import BoardManager
from OfferManager import OfferManager

class LogOnError (StandardError): pass

class Connection (GObject, Thread):
    
    __gsignals__ = {
        'connected':    (SIGNAL_RUN_FIRST, None, ()),
        'disconnected': (SIGNAL_RUN_FIRST, None, ()),
        'error':        (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, host, port, username, password):
        GObject.__init__(self)
        Thread.__init__(self)
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        self.connected = False
        self.connecting = False
        
        self.regexps = {}
    
    def expect (self, regexp, func, flag=None):
        if flag != None:
            r = re.compile(regexp, flag)
        else: r = re.compile(regexp)
        
        if r in self.regexps:
            self.regexps[r].append(func)
        else:
            self.regexps[r] = [func]
    
    def unexpect (self, func):
        for regexp, funcs in self.regexps.items():
            try:
                index = funcs.index(func)
                if len(funcs) <= 1:
                    del self.regexps[regexp]
                else:
                    del funcs[index]
            except ValueError:
                pass
    
    def cancel (self):
        raise NotImplementedError()
    
    def disconnect (self):
        raise NotImplementedError()
    
    def getUsername (self):
        raise NotImplementedError()
    
    def isRegistred (self):
        raise NotImplementedError()
    
    def isConnected (self):
        return self.connected
    
    def isConnecting (self):
        return self.connecting

EOF = _("The connection was broken - got \"end of file\" message")
NOTREG = _("'%s' is not a registered name")
BADNAM = _("Names can only consist of lower and upper case letters")
BADPAS = _("The entered password was invalid.\n\n" + \
           "If you have forgot your password, try logging in as a guest and open chat on channel 4. Write \"I've forgotten my password\" to get help.\n\n"+\
           "If that is by some reason not possible, please email: support@freechess.org")

class FICSConnection (Connection):
    def __init__ (self, host, port, username="guest", password=""):
        Connection.__init__(self, host, port, username, password)
        self.registred = None
    
    def _connect (self):
        self.connecting = True
        try:
            self.client = VerboseTelnet()
            
            try:
                self.client.open(self.host, self.port)
            except socket.gaierror, e:
                raise IOError, e.args[1]
            except EOFError:
                raise IOError, EOF
            except socket.error, e:
                raise InterruptError, ", ".join(map(str,e.args))
            except Exception, e:
                raise IOError, str(e)
            
            self.client.read_until("login: ")
            print >> self.client, self.username
            
            if self.username != "guest":
                r = self.client.expectList([
                    "password: ",
                    "login: ",
                    "Press return to enter the server as"]).next()
                if r[0] < 0:
                    raise IOError, EOF
                elif r[0] == 1:
                    raise LogOnError, BADNAM 
                elif r[0] == 2:
                    raise LogOnError, NOTREG % username
                else:
                    print >> self.client, self.password
                    self.registred = True
            else:
                self.client.read_until("Press return")
                print >> self.client
                self.registred = False
            
            r = self.client.expectList([
                "Invalid password",
                "Starting FICS session as (\w+)(?:\(([CUHIFWM])\))?"]).next()
            
            if r[0] == 0:
                raise LogOnError, BADPAS
            elif r[0] == 1:
                self.username = r[1][0]
            
            self.client.read_until("fics%")
            
            self.dm = DisconnectManager(self)
            self.glm = GameListManager(self)
            self.fm = FingerManager(self)
            self.nm = NewsManager(self)
            self.bm = BoardManager(self)
            self.om = OfferManager(self)
            
            self.connecting = False
            self.connected = True
            self.emit("connected")
        
        finally:
            self.connecting = False
    
    def run (self):
        try:
            self._connect()
            while self.isConnected():
                for match in self.client.expect(self.regexps):
                    if match[0] < 0:
                        connected = False
                        break
                    funcs, groups = match
                    for func in funcs:
                        func(self.client, groups)
            self.emit("disconnected")
        
        except Exception, e:
            if self.connected:
                self.connected = False
                for errortype in (IOError, LogOnError, InterruptError, EOFError,
                                  socket.error, socket.gaierror, socket.herror):
                    if isinstance(e, errortype):
                        self.emit("error", e)
                        break
                else:
                    raise
    
    def disconnect (self):
        self.connected = False
        self.client.close()
    
    def isRegistred (self):
        assert self.registred != None
        return self.registred
    
    def getUsername (self):
        assert self.username != None
        return self.username
