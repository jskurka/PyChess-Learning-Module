""" This module intends to work as glue between the gamemodel and the gamewidget
    taking care of stuff that is neither very offscreen nor very onscreen
    like bringing up dialogs and """

import math

import gtk

from pychess.Utils.const import *
from pychess.System import conf
from pychess.System import glock

from pychess.widgets import preferencesDialog

from gamewidget import getWidgets
from gamewidget import MENU_ITEMS, ACTION_MENU_ITEMS


def nurseGame (gmwidg, gamemodel):
    """ Call this function when gmwidget is just created """
    
    gmwidg.connect("infront", on_gmwidg_infront)
    
    gamemodel.connect("game_loaded", game_loaded, gmwidg)
    gamemodel.connect("game_saved", game_saved, gmwidg)
    gamemodel.connect("game_ended", game_ended, gmwidg)
    gamemodel.connect("game_started", on_game_started, gmwidg)

#===============================================================================
# Gamewidget signals
#===============================================================================

def on_gmwidg_infront (gmwidg):
    # Set right sensitivity states in menubar, when tab is switched
    auto = gmwidg.gamemodel.players[0].__type__ != LOCAL and \
            gmwidg.gamemodel.players[1].__type__ != LOCAL
    for item in ACTION_MENU_ITEMS:
        getWidgets()[item].props.sensitive = not auto

#===============================================================================
# Gamemodel signals
#===============================================================================

# Connect game_loaded, game_saved and game_ended to statusbar
def game_loaded (gamemodel, uri, gmwidg):
    if type(uri) in (str, unicode):
        s = "%s: %s" % (_("Loaded game"), str(uri))
    else: s = _("Loaded game")
    
    glock.acquire()
    try:
        gmwidg.status(s)
    finally:
        glock.release()

def game_saved (gamemodel, uri, gmwidg):
    glock.acquire()
    try:
        gmwidg.status("%s: %s" % (_("Saved game"), str(uri)))
    finally:
        glock.release()

def game_ended (gamemodel, reason, gmwidg):
    m1 = {
        DRAW: _("The game ended in a draw"),
        WHITEWON: _("White player won the game"),
        BLACKWON: _("Black player won the game"),
        KILLED: _("The game has been killed"),
        ADJOURNED: _("The game has been adjourned"),
        ABORTED: _("The game has been aborted"),
    }[gamemodel.status]
    m2 = {
        DRAW_INSUFFICIENT: _("caused by insufficient material"),
        DRAW_REPITITION: _("as the same position was repeated three times in a row"),
        DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
        DRAW_CALLFLAG: _("as both players ran out of time"),
        DRAW_STALEMATE: _("because of stalemate"),
        DRAW_AGREE: _("as the players agreed to"),
        DRAW_ADJUDICATION: _("as decided by an admin"),
        DRAW_LENGTH: _("as game exceed the max length"),
        
        WON_RESIGN: _("as opponent resigned"),
        WON_CALLFLAG: _("as opponent ran out of time"),
        WON_MATE: _("on a mate"),
        WON_DISCONNECTION: _("as opponent disconnected"),
        WON_ADJUDICATION:  _("as decided by an admin"),
        
        ADJOURNED_LOST_CONNECTION: _("as a player lost connection"),
        ADJOURNED_AGREEMENT: _("as the players agreed to"),
        ADJOURNED_SERVER_SHUTDOWN: _("as the server was shut down"),
        
        ABORTED_ADJUDICATION: _("as decided by an admin"),
        ABORTED_AGREEMENT: _("as the players agreed to"),
        ABORTED_COURTESY: _("by courtesy by a player"),
        ABORTED_EARLY: _("in the early phase of the game"),
        ABORTED_SERVER_SHUTDOWN: _("as the server was shut down"),
        
        WHITE_ENGINE_DIED: _("as the white engine died"),
        BLACK_ENGINE_DIED: _("as the black engine died"),
        UNKNOWN_REASON: _("by no known reason")
    }[reason]
    
    glock.acquire()
    try:
        md = gtk.MessageDialog()
        md.set_markup(_("<b><big>%s</big></b>") % m1)
        md.format_secondary_markup(m2)
        gmwidg.showMessage(md)
        gmwidg.status("%s %s" % (m1,m2))
        
        if reason == WHITE_ENGINE_DIED:
            engineDead(gamemodel.players[0], gmwidg)
        elif reason == BLACK_ENGINE_DIED:
            engineDead(gamemodel.players[1], gmwidg)
    finally:
        glock.release()

def on_game_started (gamemodel, gmwidg):
    # Rotate to human player
    boardview = gmwidg.board.view
    if gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ != LOCAL:
            boardview.rotation = math.pi
        elif conf.get("autoRotate", True) and \
                gamemodel.curplayer == gamemodel.players[1]:
            boardview.rotation = math.pi
    
    # Play set-up sound
    if conf.get("useSounds", False):
        preferencesDialog.SoundTab.playAction("gameIsSetup")
    
    # Connect player offers to statusbar
    for player in gamemodel.players:
        if player.__type__ == LOCAL:
            player.connect("offer", offer_callback, gmwidg)
    
    # Start analyzers if any
    setAnalyzerEnabled(gmwidg, HINT, getWidgets()["hint_mode"].get_active())
    setAnalyzerEnabled(gmwidg, SPY, getWidgets()["spy_mode"].get_active())

#===============================================================================
# Player signals
#===============================================================================

def offer_callback (player, offer, gmwidg):
    if offer.offerType == DRAW_OFFER:
        if gamemodel.status != RUNNING:
            return # If the offer has already been handled by
                   # Gamemodel and the game was drawn, we need
                   # to do nothing
        glock.acquire()
        try:
            gmwidg.status(_("You sent a draw offer"))
        finally:
            glock.release()

#===============================================================================
# Subfunctions
#===============================================================================

def engineDead (engine, gmwidg):
    gmwidg.bringToFront()
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

def setAnalyzerEnabled (gmwidg, analyzerType, enabled):
    print "a", analyzerType in gmwidg.gamemodel.spectactors, gmwidg.gamemodel.spectactors
    if not analyzerType in gmwidg.gamemodel.spectactors:
        return
    
    analyzer = gmwidg.gamemodel.spectactors[analyzerType]
    
    if analyzerType == HINT:
        arrow = gmwidg.board.view._set_greenarrow
    else: arrow = gmwidg.board.view._set_redarrow
    set_arrow = lambda x: gmwidg.board.view.runWhenReady(arrow, x)
    
    if enabled:
        if len(analyzer.analyzeMoves) >= 1:
            if gmwidg.gamemodel.curplayer.__type__ == LOCAL:
                set_arrow (analyzer.analyzeMoves[0].cords)
            else: set_arrow (None)
        
        # This is a kludge using pythons ability to asign attributes to an
        # object, even if those attributes are nowhere mentioned in the objects
        # class. So don't go looking for it ;)
        # Code is used to save our connection ids, enabling us to later dis-
        # connect
        if not hasattr (gmwidg.gamemodel, "anacons"):
            gmwidg.gamemodel.anacons = {HINT:[], SPY:[]}
        if not hasattr (gmwidg.gamemodel, "chacons"):
            gmwidg.gamemodel.chacons = []
        
        def on_analyze (analyzer, moves):
            if gmwidg.gamemodel.curplayer.__type__ == LOCAL and moves:
               set_arrow (moves[0].cords)
            else: set_arrow (None)
            
        def on_game_change (gamemodel):
            set_arrow (None)
        
        gmwidg.gamemodel.anacons[analyzerType].append(
                analyzer.connect("analyze", on_analyze))
        gmwidg.gamemodel.chacons.append(
                gmwidg.gamemodel.connect("game_changed", on_game_change))
    
    else:
        if hasattr (gmwidg.gamemodel, "anacons"):
            for conid in gmwidg.gamemodel.anacons[analyzerType]:
                analyzer.disconnect(conid)
            del gmwidg.gamemodel.anacons[analyzerType][:]
        if hasattr (gmwidg.gamemodel, "chacons"):
            for conid in gmwidg.gamemodel.chacons:
                gmwidg.gamemodel.disconnect(conid)
            del gmwidg.gamemodel.chacons[:]
        set_arrow (None)


