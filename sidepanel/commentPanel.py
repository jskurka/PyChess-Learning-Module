# -*- coding: UTF-8 -*-

import gtk, pango
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import *
from pychess.Utils.lutils.lsort import staticExchangeEvaluate
from pychess.Utils.lutils.lmove import FLAG, TCORD, FCORD, toSAN
from pychess.Utils.lutils.lmovegen import genCaptures
from pychess.Utils.lutils.leval import evalMaterial
from pychess.Utils.lutils import ldata
from pychess.Utils.lutils import strateval

__title__ = _("Comments")

class Sidepanel:
    
    def __init__ (self):
        self.givenTips = {}
        
    def load (self, gmwidg):
        
        self.gamemodel = gmwidg.widgets["board"].view.model
        self.gamemodel.connect("game_changed", self.game_changed)
        self.gamemodel.connect("moves_undoing", self.moves_undoing)
        
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        scrollwin = widgets.get_widget("scrolledwindow")
        scrollwin.unparent()
        
        self.store = gtk.ListStore(str)
        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(gtk.SELECTION_BROWSE)
        r = gtk.CellRendererText()
        r.set_property("wrap-width", 177) #FIXME: Fixed width size
        r.set_property("wrap-mode", pango.WRAP_WORD)
        self.tv.append_column(gtk.TreeViewColumn("Comment", r, text=0))
        
        self.tv.get_selection().connect_after('changed', self.select_cursor_row)
        self.boardview = gmwidg.widgets["board"].view
        self.boardview.connect("shown_changed", self.shown_changed)
        
        def changed (vadjust):
            if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
                vadjust.set_value(vadjust.upper-vadjust.page_size)
                vadjust.need_scroll = True
        scrollwin.get_vadjustment().connect("changed", changed)
        
        def value_changed (vadjust):
            vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - \
            		vadjust.upper) < vadjust.step_increment
        scrollwin.get_vadjustment().connect("value-changed", value_changed)
        
        self.store.append([_("Initial position")])
        
        self.frozen = False
        
        return scrollwin
    
    def select_cursor_row (self, selection):
        iter = selection.get_selected()[1]
        if iter == None: return
        if self.frozen: return
        row = self.tv.get_model().get_path(iter)[0]
        self.boardview.shown = self.gamemodel.lowply+row
    
    def shown_changed (self, boardview, shown):
        row = shown + self.gamemodel.lowply
        if row >= len(self.store): return
        iter = self.store.get_iter(row)
        self.tv.get_selection().select_iter(iter)
    
    def addComment (self, text):
        self.__widget__.set_text(self.__widget__.get_text()+"\n"+text)
    
    def moves_undoing (self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        model = self.tv.get_model()
        for i in xrange(moves):
            model.remove(model.get_iter( (len(model)-1,) ))
    
    def game_changed (self, model):
        
        def addComment (comment):
            self.store.append([comment])
            
            iter = self.tv.get_selection().get_selected()[1]
            if iter:
                row = self.tv.get_model().get_path(iter)[0]
                if row < self.boardview.shown-1:
                    return
            
            self.frozen = True
            iter = self.store.get_iter(len(self.store)-1)
            self.tv.get_selection().select_iter(iter)
            self.frozen = False
        
        ########################################################################
        # Set up variables
        ########################################################################
        
        board = model.boards[-1].board
        oldboard = model.boards[-2].board
        color = oldboard.color
        s, phase = evalMaterial (board)
        
        #   * Final: Will be shown alone: "mates", "draws"
        #   * Prefix: Will always be shown: "castles", "promotes"
        #   * Attack: Will always be shown: "threaten", "preassures", "defendes"
        #   * Moves (s): Will always be shown: "put into *"
        #   * State: (s) Will always be shown: "new *"
        #   * Simple: (s) Max one will be shown: "develops", "activity"
        #   * Tip: (s) Will sometimes be shown: "pawn storm", "cramped position"
        
        ########################################################################
        # Call strategic evaluation functions
        ########################################################################
        
        def getMessages (prefix):
            messages = []
            # We have to lock board and oldboard, as some of the eval functions
            # does funny things with them.
            # I'm not sure if this is nessesery, as no other threads I know of
            # are running in our process (the main one)...
            oldboard.lock.acquire()
            board.lock.acquire()
            for functionName in dir(strateval):
                if not functionName.startswith(prefix+"_"): continue
                function = getattr(strateval, functionName)
                for message in function (model, phase):
                    messages.append(message)
            board.lock.release()
            oldboard.lock.release()
            return messages
        
        #move = model.moves[-1].move
        #print "----- %d - %s -----" % (model.ply/2, toSAN(oldboard, move))
        
        # ----------------------------------------------------------------------
        # Final
        # ----------------------------------------------------------------------
        
        messages = getMessages ("final")
        if messages:
            addComment ("%s %s" % (reprColor[color], messages[0]))
            return
        
        # ---
        
        strings = []
        
        # ----------------------------------------------------------------------
        # Attacks
        # ----------------------------------------------------------------------
        
        messages = getMessages ("attack")
        for message in messages:
            strings.append("%s %s" % (reprColor[color], message))
        
        # ----------------------------------------------------------------------
        # Check for prefixs
        # ----------------------------------------------------------------------
        
        messages = getMessages ("prefix")
        if messages:
            string = "%s %s" % (reprColor[color], messages[0])
        else: string = ""
        
        # ----------------------------------------------------------------------
        # Check for special move stuff
        # ----------------------------------------------------------------------
        
        messages = getMessages ("moves")
        for message in messages:
            if not string:
                string = "%s %s" % (reprColor[color], message)
            else: string += " and %s" % message
        
        if string:
            strings.append(string)
        
        # ----------------------------------------------------------------------
        # Simple
        # ----------------------------------------------------------------------
        
        # We only add simples if there hasn't been too much stuff to say
        if not strings:
            messages = getMessages ("simple")
            if messages:
                messages.sort(reverse=True)
                score, message = messages[0]
                strings.append("%s %s" % (reprColor[color], message))
        
        # ----------------------------------------------------------------------
        # State
        # ----------------------------------------------------------------------
        
        messages = getMessages("state")
        messages.sort(reverse=True)
        for score, message in messages:
            strings.append(message)
        
        # ----------------------------------------------------------------------
        # Tips
        # ----------------------------------------------------------------------
        
        tips = getMessages("tip")
        tips.sort(reverse=True)
        
        for (score, tip) in tips:
            if tip in self.givenTips:
                oldscore, ply = self.givenTips[tip]
                if score < oldscore*1.3 or model.ply < ply+10:
                    continue
            
            self.givenTips[tip] = (score, model.ply)
            strings.append(tip)
            break
        
        # ----------------------------------------------------------------------
        # Last solution
        # ----------------------------------------------------------------------
        
        if not strings:
            tcord = TCORD(model.moves[-1].move)
            piece = board.arBoard[tcord]
            strings.append( _("%s moves a %s to %s") % \
                    (reprColor[color], reprPiece[piece], reprCord[tcord]) )
        
        addComment (";\n".join(strings))
