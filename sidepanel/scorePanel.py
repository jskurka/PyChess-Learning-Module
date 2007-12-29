
from math import e
from random import randint
from sys import maxint

import gtk, gobject
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.glock import glock_connect
from pychess.Utils.const import WHITE, DRAW, RUNNING, WHITEWON, BLACKWON

class ScorePlot (gtk.DrawingArea):
    
    __gtype_name__ = "ScorePlot"+str(randint(0,maxint))
    
    __gsignals__ = {
        "selected" : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,))
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
    
    def undo (self):
        del self.scores[-1]
    
    def select (self, index):
        self.selected = index
    
    def clear (self):
        del self.scores[:]
    
    def redraw (self):
        if self.window:
            a = self.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, a.width, a.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
    
    def press (self, widget, event):
        self.emit('selected', event.y/self.moveHeight)
    
    def expose (self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        self.set_size_request(-1, (len(self.scores))*self.moveHeight)
        return False
    
    def draw (self, cr):

        width = self.get_allocation().width
        height = len(self.scores)*self.moveHeight
        
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
        cr.line_to(width/2., 0)
        for i, score in enumerate(self.scores):
            score2 = -1+e**(-1./1000*abs(score/2.))
            if score > 0: score2 = -score2
            x = width/2 + score2*width/2
            y = (i+1) * self.moveHeight
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
        
        lw = 2.
        cr.set_line_width(lw)
        y = (self.selected)*self.moveHeight
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
    
    def load (self, gmwidg):
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
        glock_connect(self.boardview.model, "game_changed", self.game_changed)
        glock_connect(self.boardview.model, "moves_undoing", self.moves_undoing)
        
        # Add the initial board
        self.game_changed (self.boardview.model)
        
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
    
    def moves_undoing (self, model, moves):
        for i in xrange(moves):
            self.plot.undo()
        
        # As shown_changed will normally be emitted just after game_changed -
        # if we are viewing the latest position - we can do the selection change
        # now, and thereby avoid redraw being called twice
        if self.plot.selected == model.ply-model.lowply:
            self.plot.select(model.ply-model.lowply - moves)
        self.plot.redraw()
    
    def game_changed (self, model):
        if model.status == DRAW:
            points = 0
        elif model.status == WHITEWON:
            points = maxint
        elif model.status == BLACKWON:
            points = -maxint
        else:
            points = leval.evaluateComplete(model.boards[-1].board, WHITE, True)
        
        self.plot.addScore(points)
        
        # As shown_changed will normally be emitted just after game_changed -
        # if we are viewing the latest position - we can do the selection change
        # now, and thereby avoid redraw being called twice
        if self.plot.selected == model.ply-model.lowply -1:
            self.plot.select(model.ply-model.lowply)
        self.plot.redraw()
        
        # Uncomment this to debug eval function
        return
        
        board = model.boards[-1].board
        opboard = model.boards[-1].clone().board
        opboard.setColor(1-opboard.color)
        material, phase = leval.evalMaterial (board)
        if board.color == WHITE:
            print "material", -material
            e1 = leval.evalKingTropism (board)
            e2 = leval.evalKingTropism (opboard)
            print "evaluation: %d + %d = %d " % (e1, e2, e1+e2)
            p1 = leval.evalPawnStructure (board, phase)
            p2 = leval.evalPawnStructure (opboard, phase)
            print "pawns: %d + %d = %d " % (p1, p2, p1+p2)
            print "knights:",-leval.evalKnights (board)
            print "king:",-leval.evalKing(board,phase)
        else:
            print "material", material
            print "evaluation:",leval.evalKingTropism (board)
            print "pawns:", leval.evalPawnStructure (board, phase)
            print "pawns2:", leval.evalPawnStructure (opboard, phase)
            print "pawns3:", leval.evalPawnStructure (board, phase) + \
                             leval.evalPawnStructure (opboard, phase)
            print "knights:",leval.evalKnights (board)
            print "king:",leval.evalKing(board,phase)
        print "----------------------"
        
    def shown_changed (self, boardview, shown):
        if self.plot.selected != shown:
            self.plot.select(shown-self.boardview.model.lowply)
            self.plot.redraw()
    
    def plot_selected (self, plot, selected):
        self.boardview.shown = selected+self.boardview.model.lowply
