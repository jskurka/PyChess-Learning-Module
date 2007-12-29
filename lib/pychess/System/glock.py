from threading import RLock, currentThread
from gtk.gdk import threads_enter, threads_leave
_rlock = RLock()

def acquire():
    me = currentThread()
    # Ensure we don't deadlock if another thread is waiting on threads_enter
    # while we wait on _rlock.acquire()
    if me.getName() == "MainThread" and _rlock._RLock__owner != me:
        threads_leave()
    # Acquire the lock, if it is not ours, or add one to the recursive counter
    _rlock.acquire()
    # If it is the first time we lock, we will acquire the gdklock
    if _rlock._RLock__count == 1:
        threads_enter()

def release():
    me = currentThread()
    # As it is the natural state for the MainThread to control the gdklock, we
    # only release it if _rlock has been released so many times that we don't
    # own it any more
    if me.getName() == "MainThread":
        if _rlock._RLock__owner != me:
            threads_leave()
        else: _rlock.release()
    # If this is the last unlock, we also free the gdklock.
    elif _rlock._RLock__owner == me:
        if _rlock._RLock__count == 1:
            threads_leave()
        _rlock.release()

def glock_connect(emitter, signal, function, *args, **kwargs):
    def handler(emitter, *extra):
        acquire()
        try:
            function(emitter, *extra)
        finally:
            release()
    if "after" in kwargs and kwargs["after"]:
        return emitter.connect_after(signal, handler, *args)
    return emitter.connect(signal, handler, *args)

def glock_connect_after(emitter, signal, function, *args):
    return glock_connect(emitter, signal, function, after=True, *args)

if __name__ == "__main__":
    from threading import Thread
    def do ():
        acquire()
        acquire()
        release()
        print _rlock._RLock__owner
        print currentThread()
        release()
        print _rlock._RLock__owner
    t = Thread(target=do)
    t.start()
    t.join()
