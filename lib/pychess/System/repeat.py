# -*- coding: UTF-8 -*-

import time
from pychess.System.ThreadPool import pool

def repeat (func, *args, **kwargs):
    """ Repeats a function in a new thread until it returns False """
    def run ():
        while func(*args, **kwargs):
            pass
    pool.start(run)

def repeat_sleep (func, sleeptime, recur=False):
    """ Repeats a function aproximately each time.slepptime.time in a new thread
        until it returns False """
    def run ():
        last = time.time()
        val = None
        while True:
            time.sleep(time.time()-last + sleeptime)
            if not time:
                # If python has been shutdown while we were sleeping, the
                # imported modules will be None
                return
            last = time.time()
            if recur and val:
                val = func(val)
            else: val = func()
            if not val: break
    pool.start(run)
