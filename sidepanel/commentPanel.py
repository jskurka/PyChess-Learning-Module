# -*- coding: UTF-8 -*-

from __future__ import with_statement

import gtk, pango
from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix
from pychess.System.glock import *
from pychess.Utils.const import *
from pychess.Utils.repr import reprColor, reprPiece
from pychess.Utils.lutils.lsort import staticExchangeEvaluate
from pychess.Utils.lutils.lmove import FLAG, TCORD, FCORD, toSAN
from pychess.Utils.lutils.lmovegen import genCaptures
from pychess.Utils.lutils.leval import evalMaterial
from pychess.Utils.lutils import ldata
from pychess.Utils.lutils import strateval

__title__ = _("Comments")

__icon__ = addDataPrefix("glade/panel_comments.svg")

__desc__ = _("The comments panel will try to analyze and explain the moves played")

class Switch:
    def __init__(self): self.on = False
    def __enter__(self): self.on = True
    def __exit__(self, *a): self.on = False

class Sidepanel:

    def __init__ (self):
        self.givenTips = {}

    def load (self, gmwidg):
        
        self.gamemodel = gmwidg.board.view.model
        self.gmhandlers = [
            glock_connect(self.gamemodel, "game_changed", self.game_changed),
            glock_connect(self.gamemodel, "game_started", self.game_started),
            glock_connect(self.gamemodel, "moves_undoing", self.moves_undoing)
        ]

        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        scrollwin = widgets.get_widget("scrolledwindow")
        scrollwin.unparent()

        self.store = gtk.ListStore(str)
        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(gtk.SELECTION_BROWSE)
        #r = gtk.CellRendererText()
        #r.set_property("wrap-width", 177) #FIXME: Fixed width size
        #r.set_property("wrap-mode", pango.WRAP_WORD)
        #self.tv.append_column(gtk.TreeViewColumn("Comment", r, text=0))
        uistuff.appendAutowrapColumn(self.tv, 200, "Comment", text=0)

        self.tv.get_selection().connect_after('changed', self.select_cursor_row)
        self.boardview = gmwidg.board.view
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
        
        self.frozen = Switch()

        return scrollwin

    def select_cursor_row (self, selection):
        iter = selection.get_selected()[1]
        if iter == None: return
        if self.frozen.on: return
        row = self.tv.get_model().get_path(iter)[0]
        self.boardview.shown = self.gamemodel.lowply+row
    
    def shown_changed (self, boardview, shown):
        row = shown - self.gamemodel.lowply
        iter = self.store.get_iter(row)
        self.tv.get_selection().select_iter(iter)
    
    def moves_undoing (self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        model = self.tv.get_model()
        for i in xrange(moves):
            model.remove(model.get_iter( (len(model)-1,) ))
    
    def game_started (self, model):
        self.game_changed(model)
    def game_changed (self, model):
        for ply in xrange(len(self.store)+model.lowply, model.ply+1):
            self.addComment(model, self.__chooseComment(model, ply))
    
    def addComment (self, model, comment):
        self.store.append([comment])
        
        # If latest ply is shown, we select the new latest
        iter = self.tv.get_selection().get_selected()[1]
        if iter:
            row = self.tv.get_model().get_path(iter)[0]
            if row < self.boardview.shown-1:
                return
        
        if self.boardview.shown >= model.ply:
            iter = self.store.get_iter(len(self.store)-1)
            with self.frozen:
                self.tv.get_selection().select_iter(iter)
    
    def __chooseComment(self, model, ply):
        
        if ply == model.lowply:
            return _("Initial position")
        
        ########################################################################
        # Set up variables
        ########################################################################
        
        color = model.getBoardAtPly(ply-1).board.color
        s, phase = evalMaterial (model.getBoardAtPly(ply).board,
                                 model.getBoardAtPly(ply-1).color)
        
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
            for functionName in dir(strateval):
                if not functionName.startswith(prefix+"_"): continue
                function = getattr(strateval, functionName)
                messages.extend(function (model, ply, phase))
            return messages

        #move = model.moves[-1].move
        #print "----- %d - %s -----" % (model.ply/2, toSAN(oldboard, move))

        # ----------------------------------------------------------------------
        # Final
        # ----------------------------------------------------------------------

        messages = getMessages ("final")
        if messages:
            return "%s %s" % (reprColor[color], messages[0])

        # ---

        strings = []

        # ----------------------------------------------------------------------
        # Attacks
        # ----------------------------------------------------------------------

        messages = getMessages ("attack")
        for message in messages:
            strings.append("%s %s" % (reprColor[color], message))

        # ----------------------------------------------------------------------
        # Check for prefixes
        # ----------------------------------------------------------------------

        messages = getMessages ("prefix")
        if messages:
            prefix = messages[0]
        else: prefix = ""

        # ----------------------------------------------------------------------
        # Check for special move stuff. All of which accept prefixes
        # ----------------------------------------------------------------------

        for message in getMessages("offencive_moves") \
                       + getMessages("defencive_moves"):
            if prefix:
                strings.append("%s %s %s %s" %
                              (reprColor[color], prefix, _("and"), message))
                prefix = ""
            else:
                strings.append("%s %s" % (reprColor[color], message))

        # ----------------------------------------------------------------------
        # Simple
        # ----------------------------------------------------------------------

        # We only add simples if there hasn't been too much stuff to say
        if not strings:
            messages = getMessages ("simple")
            if messages:
                messages.sort(reverse=True)
                score, message = messages[0]
                if prefix:
                    strings.append("%s %s %s %s" %
                                  (reprColor[color], prefix, _("and"), message))
                    prefix = ""

        # ----------------------------------------------------------------------
        # Prefix fallback
        # ----------------------------------------------------------------------

        # There was nothing to apply the prefix to, so we just post it here
        # before the states and tips
        if prefix:
            strings.append("%s %s" % (reprColor[color], prefix))
            prefix = ""

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
                oldscore, oldply = self.givenTips[tip]
                if score < oldscore*1.3 or model.ply < oldply+10:
                    continue

            self.givenTips[tip] = (score, model.ply)
            strings.append(tip)
            break

        # ----------------------------------------------------------------------
        # Last solution
        # ----------------------------------------------------------------------

        if not strings:
            tcord = TCORD(model.getMoveAtPly(ply-1).move)
            piece = model.getBoardAtPly(ply).board.arBoard[tcord]
            strings.append( _("%(color)s moves a %(piece)s to %(cord)s") % {
                'color': reprColor[color], 'piece': reprPiece[piece], 'cord': reprCord[tcord]})
        
        return ";\n".join(strings)
