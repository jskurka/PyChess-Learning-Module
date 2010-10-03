""" This module intends to work as glue between the gamemodel and the gamewidget
    taking care of stuff that is neither very offscreen nor very onscreen
    like bringing up dialogs and """

import math

import gtk

from pychess.Utils.Offer import Offer
#from pychess.Utils.GameModel import GameModel
#from pychess.Utils.TimeModel import TimeModel

from pychess.Utils.const import *
import pychess.ic.ICGameModel
from pychess.Utils.repr import *
from pychess.System import conf
from pychess.System import glock

from pychess.widgets import preferencesDialog

from gamewidget import getWidgets, key2gmwidg, isDesignGWShown
from gamewidget import MENU_ITEMS, ACTION_MENU_ITEMS
from pychess.ic.ICGameModel import ICGameModel


def nurseGame (gmwidg, gamemodel):
    """ Call this function when gmwidget is just created """
    
    gmwidg.connect("infront", on_gmwidg_infront)
    gmwidg.connect("closed", on_gmwidg_closed)
    gmwidg.connect("title_changed", on_gmwidg_title_changed)
    
    # Because of the async loading of games, the game might already be started,
    # when the glock is ready and nurseGame is called.
    # Thus we support both cases.
    if gamemodel.status == WAITING_TO_START:
        gamemodel.connect("game_started", on_game_started, gmwidg)
        gamemodel.connect("game_loaded", game_loaded, gmwidg)
    else:
        if gamemodel.uri:
            game_loaded(gamemodel, gamemodel.uri, gmwidg)
        on_game_started(gamemodel, gmwidg)
    
    gamemodel.connect("game_saved", game_saved, gmwidg)
    gamemodel.connect("game_ended", game_ended, gmwidg)
    gamemodel.connect("game_unended", game_unended, gmwidg)
    gamemodel.connect("game_resumed", game_unended, gmwidg)

#===============================================================================
# Gamewidget signals
#===============================================================================

def on_gmwidg_infront (gmwidg):
    # Set right sensitivity states in menubar, when tab is switched
    auto = gmwidg.gamemodel.players[0].__type__ != LOCAL and \
            gmwidg.gamemodel.players[1].__type__ != LOCAL
    for item in ACTION_MENU_ITEMS:
        getWidgets()[item].props.sensitive = not auto
    
    for widget in MENU_ITEMS:
        sensitive = False
        if widget == 'abort':
            if isinstance(gmwidg.gamemodel, pychess.ic.ICGameModel.ICGameModel):
                sensitive = True
        elif widget == 'adjourn':
            if isinstance(gmwidg.gamemodel, pychess.ic.ICGameModel.ICGameModel):
                sensitive = True
        elif widget == 'hint_mode':
            if gmwidg.gamemodel.hintEngineSupportsVariant and conf.get("analyzer_check", True):
                sensitive = True
        elif widget == 'spy_mode':
            if gmwidg.gamemodel.spyEngineSupportsVariant and conf.get("inv_analyzer_check", True):
                sensitive = True
        elif widget == 'show_sidepanels':
            if not isDesignGWShown():
                sensitive = True
        else: sensitive = True
        getWidgets()[widget].set_property('sensitive', sensitive)
    
    # Change window title
    getWidgets()['window1'].set_title('%s - PyChess' % gmwidg.getTabText())

def on_gmwidg_closed (gmwidg):
    if len(key2gmwidg) == 1:
        getWidgets()['window1'].set_title('%s - PyChess' % _('Welcome'))

def on_gmwidg_title_changed (gmwidg):
    if gmwidg.isInFront():
        getWidgets()['window1'].set_title('%s - PyChess' % gmwidg.getTabText())

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
    
    nameDic = {"white": gamemodel.players[WHITE],
               "black": gamemodel.players[BLACK],
               "mover": gamemodel.curplayer}
    if gamemodel.status == WHITEWON:
        nameDic["winner"] = gamemodel.players[WHITE]
        nameDic["loser"] = gamemodel.players[BLACK]
    elif gamemodel.status == BLACKWON:
        nameDic["winner"] = gamemodel.players[BLACK]
        nameDic["loser"] = gamemodel.players[WHITE]
    
    m1 = reprResult_long[gamemodel.status] % nameDic
    m2 = reprReason_long[reason] % nameDic
    
    
    md = gtk.MessageDialog()
    md.set_markup("<b><big>%s</big></b>" % m1)
    md.format_secondary_markup(m2)
    
    if gamemodel.players[0].__type__ == LOCAL or gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ == REMOTE or gamemodel.players[1].__type__ == REMOTE:
            md.add_button(_("Offer Rematch"), 0)
        else:
            md.add_button(_("Play Rematch"), 1)
            if gamemodel.ply > 1:
                md.add_button(_("Undo two moves"), 2)
            elif gamemodel.ply == 1:
                md.add_button(_("Undo one move"), 2)
    
    def cb (messageDialog, responseId):
        if responseId == 0:
            if gamemodel.players[0].__type__ == REMOTE:
                gamemodel.players[0].offerRematch()
            else:
                gamemodel.players[1].offerRematch()
        elif responseId == 1:
            from pychess.widgets.newGameDialog import createRematch
            createRematch(gamemodel)
        elif responseId == 2:
            if gamemodel.curplayer.__type__ == LOCAL and gamemodel.ply > 1:
                offer = Offer(TAKEBACK_OFFER, gamemodel.ply-2)
            else:
                offer = Offer(TAKEBACK_OFFER, gamemodel.ply-1)
            if gamemodel.players[0].__type__ == LOCAL:
                gamemodel.players[0].emit("offer", offer)
            else: gamemodel.players[1].emit("offer", offer)
    md.connect("response", cb)
    
    glock.acquire()
    try:
        gmwidg.showMessage(md)
        gmwidg.status("%s %s." % (m1,m2[0].lower()+m2[1:]))
        
        if reason == WHITE_ENGINE_DIED:
            engineDead(gamemodel.players[0], gmwidg)
        elif reason == BLACK_ENGINE_DIED:
            engineDead(gamemodel.players[1], gmwidg)
    finally:
        glock.release()

def game_unended (gamemodel, gmwidg):
    glock.acquire()
    try:
        print "sending hideMessage"
        gmwidg.hideMessage()
        gmwidg.status("")
    finally:
        glock.release()

def on_game_started (gamemodel, gmwidg):
    on_gmwidg_infront(gmwidg)  # setup menu items sensitivity

    # Rotate to human player
    boardview = gmwidg.board.view
    if gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ != LOCAL:
            boardview.rotation = math.pi
        elif conf.get("autoRotate", True) and \
                gamemodel.curplayer == gamemodel.players[1]:
            boardview.rotation = math.pi
    
    # Play set-up sound
    preferencesDialog.SoundTab.playAction("gameIsSetup")
    
    # Connect player offers to statusbar
    for player in gamemodel.players:
        if player.__type__ == LOCAL:
            player.connect("offer", offer_callback, gamemodel, gmwidg)
    
    # Start analyzers if any
    setAnalyzerEnabled(gmwidg, HINT, getWidgets()["hint_mode"].get_active())
    setAnalyzerEnabled(gmwidg, SPY, getWidgets()["spy_mode"].get_active())

#===============================================================================
# Player signals
#===============================================================================

def offer_callback (player, offer, gamemodel, gmwidg):
    if offer.type == DRAW_OFFER:
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
    if not analyzerType in gmwidg.gamemodel.spectactors:
        return
    
    analyzer = gmwidg.gamemodel.spectactors[analyzerType]
    
    if analyzerType == HINT:
        arrow = gmwidg.board.view._set_greenarrow
    else: arrow = gmwidg.board.view._set_redarrow
    set_arrow = lambda x: gmwidg.board.view.runWhenReady(arrow, x)
    
    if enabled:
        if len(analyzer.getAnalysis()) >= 1:
            if gmwidg.gamemodel.curplayer.__type__ == LOCAL or \
               [player.__type__ for player in gmwidg.gamemodel.players] == [REMOTE, REMOTE]:
                set_arrow (analyzer.getAnalysis()[0].cords)
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
        
        def on_analyze (analyzer, moves, score):
            if moves and (gmwidg.gamemodel.curplayer.__type__ == LOCAL or \
               [player.__type__ for player in gmwidg.gamemodel.players] == [REMOTE, REMOTE]):
                set_arrow (moves[0].cords)
            else: set_arrow (None)
        
        def on_game_change (gamemodel):
            set_arrow (None)
        
        gmwidg.gamemodel.anacons[analyzerType].append(
                analyzer.connect("analyze", on_analyze))
        gmwidg.gamemodel.chacons.append(
                gmwidg.gamemodel.connect("game_changed", on_game_change))
        gmwidg.gamemodel.chacons.append(
                gmwidg.gamemodel.connect("moves_undoing",
                                         lambda model, moves: on_game_change(model)))
    
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


