#session

import socket, errno
import telnetlib
import re
import gobject
import random
import time
import platform
import getpass

from pychess.System.Log import log

ENCODE = [ord(i) for i in "Timestamp (FICS) v1.0 - programmed by Henrik Gram."]
ENCODELEN = len(ENCODE)
G_RESPONSE = '\x029'
FILLER = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
g_testing = False

class SessionException(Exception):
    def __init__(self, str):
        Exception.__init__(self, str)

IAC_WONT_ECHO = ''.join([telnetlib.IAC, telnetlib.WONT, telnetlib.ECHO])

class TimeSeal:
    BUFFER_SIZE = 4096

    def open (self, address, port):
        self.port = port
        self.address = address
        
        self.session_handle = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        self.stateinfo = None
        
        try:
            sock.connect((address,port))
        except socket.error, (err, desc):
            if err != errno.EINPROGRESS:
                raise
        self.sock = sock
        self.buf = ''
        
        gobject.io_add_watch(self.sock.fileno(), gobject.IO_OUT,
                lambda ch, cond: self.on_ready())
        
        import Queue
        queue = Queue.Queue()
        gobject.io_add_watch(self.sock.fileno(), gobject.IO_IN, lambda ch, cond: queue.put(None) or False)
        queue.get()
    
    def close (self):
        self.sock.close()
    
    def on_ready(self):
        self.sock.send(self.encode(self.get_init_string()))
        self.sock.setblocking(True)
        return False
    
    #get time elapsed in milliseconds since the start of app
    def get_time(self):
        now = time.time()
        intnow = int(now)
        secs = 1000 * (intnow%10000)
        millis = int((now - intnow)*1000)
        res = secs + millis
        #print "TIME:", res, "S,M",(secs,millis)
        return res
    
    def encode(self, inbuf, timestamp = None):
        timestamp = timestamp or self.get_time()
        enc = inbuf + '\x18' + str(timestamp) + '\x19'
        padding = 11 - ((len(enc) - 1) % 12)
        filler = [random.choice(FILLER) for x in range(padding)]
        if g_testing:
            filler = [FILLER[0]] * padding
        enc += ''.join(filler)
    
        buf = [ord(i) for i in enc]
    
        for i in range(0, len(buf), 12):
            buf[i + 11], buf[i] = buf[i], buf[i + 11]
            buf[i + 9], buf[i + 2] = buf[i + 2], buf[i + 9]
            buf[i + 7], buf[i + 4] = buf[i + 4], buf[i + 7]
    
        if g_testing:
            j = encode_offset = 0
        else:
            j = encode_offset = random.randint(0, ENCODELEN-1)
    
        for i in range(0, len(buf)):
            buf[i] |= 0x80
            buf[i] = chr((buf[i] ^ ENCODE[j]) - 32)
            j += 1
            if j>= ENCODELEN: j = 0
    
        buf.append( chr(0x80 | encode_offset))
        buf.append(chr(10)) #nl
    
        return ''.join(buf)

    def get_init_string(self):
        """ timeseal header: TIMESTAMP|bruce|Linux gruber 2.6.15-gentoo-r1 #9
            PREEMPT Thu Feb 9 20:09:47 GMT 2006 i686 Intel(R) Celeron(R) CPU
            2.00GHz GenuineIntel GNU/Linux| 93049 """  
        user = getpass.getuser()
        uname = ' '.join(list(platform.uname()))
        return  "TIMESTAMP|%(user)s|%(uname)s|" % locals()
    
    def decode(self, buf, stateinfo = None):
        expected_table = "\n\r[G]\n\r"
        final_state = len(expected_table)
        g_count = 0
        result = []
    
        if stateinfo:
            state, lookahead = stateinfo
        else:
            state, lookahead = 0, []
    
        lenb = len(buf)
        idx = 0
        while idx < lenb:
            ch = buf[idx]
            expected = expected_table[state]
            if ch == expected:
                state += 1
                if state == final_state:
                    g_count += 1
                    lookahead = []
                    state = 0
                else:
                    lookahead.append(ch)
                idx += 1
            elif state == 0:
                result.append(ch)
                idx += 1
            else:
                result.extend(lookahead)
                lookahead = []
                state = 0
    
        return (''.join(result),g_count, (state, lookahead))
    
    def write(self, str):
        self.sock.send(self.encode(str))
    
    def readline(self):
        while True:
            i = self.buf.find("\n")
            if i >= 0:
                line = self.buf[:i+1]
                self.buf = self.buf[i+1:]
                return line
            self.cook_some()
    
    def cook_some (self):
        recv = self.sock.recv(self.BUFFER_SIZE) 
        if len(recv) == 0:
            raise SessionException("No more data")
        
        recv, g_count, self.stateinfo = self.decode(recv, self.stateinfo)
        recv = recv.replace("\r","")
        log.debug(recv, "fics")
        
        for i in range(g_count):
            print "G_RESPONSE"
            self.sock.send(self.encode(G_RESPONSE))
        
        self.buf += recv
    
    def read_until (self, *untils):
        while True:
            for i, until in enumerate(untils):
                start = self.buf.find(until)
                if start >= 0:
                    self.buf = self.buf[:start]
                    return i
            self.cook_some()
    
    def __repr__ (self):
        return "fics"

            








