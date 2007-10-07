
import os, sys, select, signal, errno, termios
from select import POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL
from termios import tcgetattr, tcsetattr
from random import randint, choice
import pty

from Log import log

pollErrDic = {
    POLLIN: "There is data to read",
    POLLPRI: "There is urgent data to read",
    POLLOUT: "Ready for output: writing will not block",
    POLLERR: "Error condition of some sort",
    POLLHUP: "Hung up",
    POLLNVAL: "Invalid request: descriptor not open",
}

ERRORS = POLLERR | POLLHUP | POLLNVAL

CHILD = 0

class SubProcessError (Exception): pass
class TimeOutError (Exception): pass

def searchPath (file):
    for dir in os.environ["PATH"].split(":"):
        path = os.path.join(dir, file)
        if os.path.isfile(path):
            return path

class SubProcess:
    """ Pty based communication wrapper """
    
    def __init__(self, path, args=[], env=None, warnwords=[]):
        self.path = path
        self.args = args
        self.env = env or os.environ
        self.warnwords = warnwords
        
        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        log.debug(path+"\n", self.defname)
        
        self.buffer = ""
        self.poll = select.poll()
        
        #self.initPty()
        self.initGlc()
        
        self.poll.register(self.fdin,
            POLLIN | POLLPRI | POLLERR | POLLHUP | POLLNVAL)
    
    def initPty (self):
        self.pid, fd = pty.fork()
        log.debug("forking %d %d" % (self.pid, fd))
        if self.pid == CHILD:
            os.nice(15)
            print "path", self.path, "args", self.args
            os.execve(self.path, [self.path]+self.args, self.env)
            os._exit(-1)
        
        # Stop our commands being echoed back
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = tcgetattr(fd)
        lflag &= ~termios.ECHO
        tcsetattr(fd, termios.TCSANOW,
        		[iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        
        self.fdin = fd
        self.fdout = fd
    
    def initGlc (self):
        
        # Pipe to communicate to engine with
        toManagerPipe = os.pipe()
        fromManagerPipe = os.pipe()
        
        # Store the file descripter for reading/writing
        self.fdout = toManagerPipe[1]
        self.fdin = fromManagerPipe[0]
        
        # Fork off a child process to manage the engine
        self.pid = os.fork()
        if self.pid == 0:
            # ..
            os.close(toManagerPipe[1])
            os.close(fromManagerPipe[0])
            
            # Make pipes to the engine
            stdinPipe = os.pipe()
            stdoutPipe = os.pipe()
            stderrPipe = os.pipe()
            
            # Fork off the engine
            engineFd = os.fork()
            if engineFd == 0:
                # Make the engine low priority for CPU usage
                os.nice(15)
                
                # Connect stdin, stdout and stderr to the manager process
                os.dup2(stdinPipe[0], sys.stdin.fileno())
                os.dup2(stdoutPipe[1], sys.stdout.fileno())
                os.dup2(stderrPipe[1], sys.stderr.fileno())
                
                # Execute the engine
                try:
                    os.execve(self.path, [self.path] + self.args, self.env)
                except OSError:
                    pass
                os._exit(0)
                
            # Catch if the child dies
            def childDied(sig, stackFrame):
                try:
                    os.waitpid(-1, os.WNOHANG)
                except OSError:
                    return
                
                # Close connection to the application
                os.close(fromManagerPipe[1])
                    
                os._exit(0)
            signal.signal(signal.SIGCHLD, childDied)

            # Forward data between the application and the engine and wait for closed pipes
            inputPipes = [toManagerPipe[0], stdoutPipe[0], stderrPipe[0]]
            pipes = [toManagerPipe[0], toManagerPipe[1], stdinPipe[0], stdinPipe[1], stdoutPipe[0], stdoutPipe[1], stderrPipe[0], stderrPipe[1]]
            while True:                
                # Wait for data
                (rfds, _, xfds) = select.select(inputPipes, [], pipes, None)
                
                for fd in rfds:
                    data = os.read(fd, 65535)
                    
                    # One of the connections has closed - kill the engine and quit
                    if len(data) == 0:
                        os.kill(engineFd, signal.SIGQUIT)
                        os._exit(0)
                    
                    # Send data from the application to the engines stdin
                    if fd == toManagerPipe[0]:
                        os.write(stdinPipe[1], data)
                    # Send engine output to the application
                    else:
                        os.write(fromManagerPipe[1], data)
            
            os._exit(0)
        
        os.close(toManagerPipe[0])
        os.close(fromManagerPipe[1])
    
    def readline (self, timeout=None):
    	
        i = self.buffer.find("\n")
        if i >= 0:
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                log.debug(line+"\n", self.defname)
                return line
        
        while True:
            try:
                readies = self.poll.poll(timeout)
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                raise
            
            if not readies:
                raise TimeOutError, "Reached %d milisec timeout" % timeout
            
            fd, event = readies[0]
            if event & ERRORS:
                errors = []
                if event & POLLERR:
                    errors.append("Error condition of some sort")
                if event & POLLHUP:
                    errors.append("Hung up")
                if event & POLLNVAL:
                    errors.append("Invalid request: descriptor not open")
                raise SubProcessError (event, errors)
            
            data = os.read(self.fdin, 1024)
            self.buffer += data.replace("\r\n","\n").replace("\r","\n")
            
            i = self.buffer.find("\n")
            if i < 0: continue
            
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                if self.warnwords:
                    lline = line.lower()
                    for word in self.warnwords:
                        if word in lline:
                            log.warn(line+"\n", self.defname)
                            break
                    else:
                        log.debug(line+"\n", self.defname)
                return line
    
    def write (self, data):
        log.log(data, self.defname)
        os.write(self.fdout, data)
    
    def wait4exit (self):
        try:
            pid, code = os.waitpid(self.pid, 0)
            log.debug(os.strerror(code)+"\n", self.defname)
        except OSError, error:
            if error.errno == errno.ECHILD:
                #No child processes
                pass
            else: raise OSError, error
    
    def sendSignal (self, sign, doclose):
        try:
            os.kill(self.pid, sign)
            if doclose:
                os.close(self.fdout)
                os.close(self.fdin)
        except OSError, error:
            if error.errno == errno.ESRCH:
                #No such process
                pass
            else: raise OSError, error
    
    def sigkill (self):
        self.sendSignal(signal.SIGKILL, True)
    
    def sigterm (self):
        self.sendSignal(signal.SIGTERM, True)
    
    def sigint (self):
        self.sendSignal(signal.SIGINT, False)

if __name__ == "__main__":
    paths = ("igang.dk", "google.com", "google.dk", "ahle.dk", "myspace.com", "yahoo.com")
    maxlen = max(len(p) for p in paths)
    ps = [(SubProcess("/bin/ping", [path]), path) for path in paths]
    for i in xrange(10):
        for subprocess, path in ps:
            print i, "\t", path.ljust(maxlen), subprocess.readline()
