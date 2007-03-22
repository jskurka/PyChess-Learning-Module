from telnetlib import Telnet
from gobject import *
import socket
from sys import maxint
from pychess.System.Log import log

class VerboseTelnet (Telnet, GObject):
    __gsignals__ = {
        'newString' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self):
        Telnet.__init__(self)
        GObject.__init__(self)
        self.interrupting = False
        
    def expect (self, list):
        """ Modified expect method, which checks ALL regexps for the one which
        mathces the earliest """
        
        re = None
        list = list[:]
        indices = range(len(list))
        for i in indices:
            if not hasattr(list[i], "search"):
                if not re: import re
                list[i] = re.compile(list[i])
        while 1:
            self.process_rawq()
            lowest = []
            for i in indices:
                m = list[i].search(self.cookedq)
                if m:
                    s = m.start()
                    if not lowest or s < lowest[0][1]:
                        lowest = [[m, s, i]]
                    elif s == lowest[0][1]:
                        lowest.append( [m, s, i] )
            maxend = 0
            for match, start, index in lowest:
                end = match.end()
                if end > maxend:
                    maxend = end
                yield (index, match.groups())
            self.cookedq = self.cookedq[maxend:]
            if lowest:
                return
            if self.eof:
                break
            self.fill_rawq()
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        yield (-1, [])
        
    def process_rawq (self):
        cooked0 = self.cookedq
        Telnet.process_rawq (self)
        cooked1 = self.cookedq
        if len(cooked1) > len(cooked0):
            log.debug (cooked1[len(cooked0):].replace("\r", ""), self.name)
    
    def write (self, data):
        log.log(data, self.name)
        Telnet.write (self, data)
    
    def open(self, host, port=0):
        self.eof = 0
        if not port:
            port = TELNET_PORT
        self.host = host
        self.port = port
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if self.interrupting:
                    self.interrupting = False
                    raise socket.error, "interrupted"
                self.sock = socket.socket(af, socktype, proto)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
        
        self.name = "%s#%s" % (host, port)
    
    def interrupt (self):
        if self.sock:
            self.sock.shutdown(socket.SHUT_RDWR)
        else:
            self.interrupting = True

from pychess.Utils.const import IC_CONNECTED, IC_DISCONNECTED

#f = open("/home/thomas/ficslog", "w")
#import sys
#def log2 (data, header=None):
    #sys.stdout.write(data)
    #sys.stdout.flush()
    #f.write(data.replace("\r",""))
    #f.flush()

client = None
connected = False
registered = False

class LogOnError (Exception): pass
class InterruptError (Exception): pass

def connect (host, port, username="guest", password=""):
    
    global client, connected, registered
    
    client = VerboseTelnet()
    def callback (client, string):
        import sys
        sys.stdout.write(string)
        sys.stdout.flush()
    client.connect("newString", callback)
    
    try:
        client.open(host, port)
    except socket.gaierror, e:
        raise IOError, e.args[1]
    except EOFError:
        raise IOError, _("The connection was broken - got end of file message")
    except socket.error, e:
        raise InterruptError, e.args[1]
    except Exception, e:
        raise IOError, str(e)
    
    client.read_until("login: ")
    print >> client, username
    
    if username != "guest":
        r = client.expect(
            ["password: ", "login: ", "Press return to enter the server as"]).next()
        if r[0] < 0:
            raise IOError, _("The connection was broken - got end of file " +
                             "message")
        elif r[0] == 1:
            raise LogOnError, _("Names can only consist of lower and upper " +
                                "case letters")
        elif r[0] == 2:
            raise LogOnError, _("'%s' is not a registered name") % username
        else:
            print >> client, password
            registered = True
    else:
        client.read_until("Press return"), host
        print >> client
    
    names = "(\w+)(?:\(([CUHIFWM])\))?"
    r = client.expect(["Invalid password", "Starting FICS session as %s" % names]).next()
    
    if r[0] == 0:
        raise LogOnError, _("The entered password was invalid.\n\nIf you have forgot your password, try logging in as a guest and to chat channel 4 to tell the supporters that you have forgot it.\n\nIf that is by some reason not possible, please email: suppord@freechess.org")
    elif r[0] == 1:
        global curname
        curname = r[1][0]
    
    client.read_until("fics%")
    
    connected = True
    for handler in connectHandlers:
        handler (client, IC_CONNECTED)
    
    EOF = False
    while True:
        for match in client.expect(regexps):
            if r[0] < 0:
                EOF = True
                break
            handler = handlers[match[0]]
            handler (client, match[1])
    
    for handler in connectHandlers:
        # Give handlers a chance no discover that the connection is closed
        handler (client, IC_DISCONNECTED)

import re
handlers = []
regexps = []
uncompiled = []
def expect (regexp, func, flag=None):
    handlers.append(func)
    if flag != None:
        r = re.compile(regexp, flag)
    else: r = re.compile(regexp)
    regexps.append(r)
    uncompiled.append(regexp)

def unexpect (func):
    try:
        i = handlers.index (func)
    except ValueError:
        return
    del handlers[i]
    del regexps[i]
    del uncompiled[i]

connectHandlers = []
def connectStatus (func):
    connectHandlers.append(func)
