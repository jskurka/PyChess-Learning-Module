#TODO: Add zoom buttons

import gtk, gobject
from math import e
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_INT
from random import randint
from sys import maxint

class ScorePlot (gtk.DrawingArea):
    
    __gtype_name__ = "ScorePlot"+str(randint(0,maxint))
    
    __gsignals__ = {
        "selected" : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))
    }
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.connect("button-press-event", self.press)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.moveHeight = 12
        self.scores = []
        self.selected = 0
        
    def addScore (self, score):
        self.scores.append(score)
    
    def select (self, index):
        self.selected = index
    
    def clear (self):
        del self.scores[:]
    
    def redraw (self):
        if self.window:
            def func():
                a = self.get_allocation()
                rect = gtk.gdk.Rectangle(0, 0, a.width, a.height)
                self.window.invalidate_rect(rect, True)
                self.window.process_updates(True)
            gobject.idle_add(func)
    
    def press (self, widget, event):
        self.emit('selected', int(event.y/self.moveHeight)+1)
    
    def expose (self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        self.set_size_request(-1, max(0,(len(self.scores)-1)*self.moveHeight))
        return False
    
    def draw (self, cr):

        width = self.get_allocation().width
        height = (len(self.scores)-1)*self.moveHeight
        
        ########################################
        # Draw background                      #
        ########################################
        
        cr.set_source_rgb (1, 1, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        
        ########################################
        # Draw dark middle line                #
        ########################################
        
        cr.set_source_rgb (0, 0, 0)
        cr.move_to(width/2., 0)
        cr.line_to(width/2., height)
        cr.set_line_width(0.15)
        cr.stroke()
        
        ########################################
        # Draw the actual plot (dark area)     #
        ########################################
        
        cr.set_source_rgb (0, 0, 0)
        cr.move_to(width, 0)
        for i, score in enumerate(self.scores):
            score2 = -1+e**(-1./1000*abs(score/2.))
            if score > 0: score2 = -score2
            x = width/2 + score2*width/2
            y = i * self.moveHeight
            cr.line_to(x, y)
        cr.line_to(width, height)
        cr.fill_preserve()
        
        ########################################
        # Draw light middle line               #
        ########################################
        
        cr.save()
        cr.clip()
        cr.set_source_rgb (1, 1, 1)
        cr.move_to(width/2., 0)
        cr.line_to(width/2., height)
        cr.set_line_width(0.15)
        cr.stroke()
        cr.restore()
        
        ########################################
        # Draw selection                       #
        ########################################
        
        if self.selected >= 1:
            lw = 2.
            cr.set_line_width(lw)
            y = (self.selected-1)*self.moveHeight
            cr.rectangle(lw/2, y-lw/2, width-lw, self.moveHeight+lw)
            col = self.get_style().base[gtk.STATE_SELECTED]
            r, g, b = map(lambda x: x/65535., (col.red, col.green, col.blue))
            cr.set_source_rgba (r, g, b, .15)
            cr.fill_preserve()
            cr.set_source_rgb (r, g, b)
            cr.stroke()
    
__title__ = _("Score")

from pychess.widgets import gamewidget
from pychess.Utils.lutils import leval

class Sidepanel:
    
    def load (self, window, gmwidg):
        self.plot = ScorePlot()
        __widget__ = gtk.ScrolledWindow()
        __widget__.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        port = gtk.Viewport()
        port.add(self.plot)
        port.set_shadow_type(gtk.SHADOW_NONE)
        __widget__.add(port)
        __widget__.show_all()

        self.boardview = gmwidg.widgets["board"].view
        
        self.plot.connect("selected", self.plot_selected)
        self.boardview.connect('shown_changed', self.shown_changed)
        self.boardview.model.connect("game_changed", self.game_changed)
        
        def changed (vadjust):
            if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
                vadjust.set_value(vadjust.upper-vadjust.page_size)
                vadjust.need_scroll = True
        __widget__.get_vadjustment().connect("changed", changed)
        
        def value_changed (vadjust):
            vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - \
            		vadjust.upper) < vadjust.step_increment
        __widget__.get_vadjustment().connect("value-changed", value_changed)
        
        return __widget__
    
    def game_changed (self, model):
        points = leval.evaluateComplete(
                                       model.boards[-1], model.boards[-1].color)
        self.plot.addScore(points)
    
    def shown_changed (self, boardview, shown):
        self.plot.select(shown)
        self.plot.redraw()
    
    def plot_selected (self, plot, selected):
        self.boardview.shown = selected
