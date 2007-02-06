import sys, gtk
import pango, gobject
import webbrowser
import atexit

from pychess.System import myconf
from pychess.Utils.const import *
from pychess.Players.Human import Human
from pychess.System.Log import log
from pychess.widgets import tipOfTheDay
from pychess.widgets import LogDialog
from pychess.widgets import gamewidget
from pychess.widgets import ionest
from pychess.widgets.Background import Background
from pychess.widgets import preferencesDialog

################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}

def engineDead (engine, gmwidg):
    gamewidget.setCurrent(gmwidg)
    gameDic[gmwidg].kill()
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

def makeLogDialogReady ():
    LogDialog.add_destroy_notify(lambda: window["log_viewer1"].set_active(0))

def makeAboutDialogReady ():
    clb = window["aboutdialog1"].get_child().get_children()[1].get_children()[2]
    window["aboutdialog1"].set_version(VERSION)
    def callback(button, *args):
        window["aboutdialog1"].hide()
        return True
    clb.connect("activate", callback)
    clb.connect("clicked", callback)
    window["aboutdialog1"].connect("delete-event", callback)

def setMode (gmwidg, mode, activated):
    if not gameDic: return
    
    gamemodel = gameDic[gmwidg]
    board = gmwidg.widgets["board"]
    analyzer = gamemodel.spectactors[mode]
    
    if mode == HINT:
        arrow = board.view._set_greenarrow
    else: arrow = board.view._set_redarrow
    set_arrow = lambda x: board.view.runWhenReady(arrow, x)
    
    if activated:
        if len(analyzer.analyzeMoves) >= 1:
            if gamemodel.curplayer.__type__ == LOCAL:
                set_arrow (analyzer.analyzeMoves[0].cords)
            else: set_arrow (None)
        
        # This is a kludge using pythons ability to asign attributes to an
        # object, even if those attributes are nowhere mentioned in the objects
        # class. So don't go looking for it ;)
        if not hasattr (gamemodel, "anacons"):
            gamemodel.anacons = [[],[]]
        if not hasattr (gamemodel, "hiscons"):
            gamemodel.hiscons = []
        
        def on_analyze (analyzer, moves):
            if gamemodel.curplayer.__type__ == LOCAL and moves:
               set_arrow (moves[0].cords)
            else: set_arrow (None)
            
        def on_game_change (gamemodel):
            set_arrow (None)
        
        gamemodel.anacons[mode].append(
                analyzer.connect("analyze", on_analyze))
        gamemodel.hiscons.append(
                gamemodel.connect("game_changed", on_game_change))
    
    else:
        if hasattr (gamemodel, "anacons"):
            for conid in gamemodel.anacons[mode]:
                analyzer.disconnect(conid)
            del gamemodel.anacons[mode][:]
        if hasattr (gamemodel, "hiscons"):
            for conid in gamemodel.hiscons:
                gamemodel.disconnect(conid)
            del gamemodel.hiscons[:]
        set_arrow (None)

class GladeHandlers:
    
    def on_ccalign_show (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]+clockHeight)
    
    def on_ccalign_hide (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]-clockHeight)
    
    def on_game_started (handler, gmwidg, gamemodel):
        for widget in ("save_game1", "save_game_as1", "properties1",
                       "close1", "action1", "vis1"):
            window[widget].set_property('sensitive', True)
        
        gmwidg.widgets["sidepanel"].connect("hide", \
            lambda w: window["side_panel1"].set_active(False))
        
        if gamemodel.timemodel != None:
            gmwidg.widgets["ccalign"].show()
        else: gmwidg.widgets["ccalign"].hide()
        
        gameDic[gmwidg] = gamemodel
        
        for player in gamemodel.players:
            player.connect("dead", engineDead, gmwidg)
        
        setMode(gmwidg, HINT, window["hint_mode"].get_active())
        setMode(gmwidg, SPY, window["spy_mode"].get_active())
        
        def game_loaded (gamemodel, uri):
            gmwidg.status("%s: %s" % (_("Loaded game"), str(uri)), True)
        gamemodel.connect("game_loaded", game_loaded)
        
        def game_saved (gamemodel, uri):
            gmwidg.status("%s: %s" % (_("Saved game"), str(uri)), True)
        gamemodel.connect("game_saved", game_saved)
        
        def game_ended (gamemodel, reason):
            m1 = {
                DRAW: _("The game ended in a draw"),
                WHITEWON: _("White player won the game"),
                BLACKWON: _("Black player won the game")
            }[gamemodel.status]
            m2 = {
                DRAW_INSUFFICIENT: _("caused by insufficient material"),
                DRAW_REPITITION: _("as the same position was repeated three" + \
                                   " times in a row"),
                DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
                DRAW_STALEMATE: _("because of stalemate"),
                DRAW_AGREE: _("as the players agreed to"),
                WON_RESIGN: _("as opponent resigned"),
                WON_CALLFLAG: _("as opponent ran out of time"),
                WON_MATE: _("on a mate"),
                UNKNOWN_REASON: _("by no known reason")
            }[reason]
            gmwidg.status("%s %s" % (m1,m2), idle_add=True)
        gamemodel.connect("game_ended", game_ended)
        
        def draw_sent (gamemodel, player):
            if player.__type__ == LOCAL:
                gmwidg.status(_("You sent a draw offer"), idle_add=True)
        gamemodel.connect("draw_sent", draw_sent)
        
        def flag_call_error (gamemodel, player, error):
            if player.__type__ == LOCAL:
                if error == NO_TIME_SETTINGS:
                    gmwidg.status(_("You can't call flag in a game without" + \
                                    " time settings"), idle_add=True)
                elif error == NOT_OUT_OF_TIME:
                    gmwidg.status(_("You can't call flag when your opponent" + \
                                    " is not out of time"), idle_add=True)
        gamemodel.connect("flag_call_error", flag_call_error)
        
    def on_game_closed (handler, gmwidg, gamemodel):
        del gameDic[gmwidg]
        
        if len (gameDic) == 0:
            for widget in ("save_game1", "save_game_as1", "properties1",
                           "close1", "action1", "vis1"):
                window[widget].set_property('sensitive', False)
    
    #          Drag 'n' Drop          #
    
    def on_drag_received (wi, context, x, y, selection, target_type, timestamp):
        uri = selection.data.strip()
        # We may have more than one file dropped. We choose only to care about
        # the first.
        uri = uri.split()[0]
        ionest.loadGame (uri)
    
    #          Game Menu          #

    def on_new_game1_activate (widget):
        ionest.newGame ()
        
    def on_load_game1_activate (widget):
        ionest.loadGame ()
    
    def on_set_up_position_activate (widget):
        ionest.setUpPosition ()
    
    def on_enter_game_notation_activate (widget):
        ionest.enterGameNotation ()
    
    def on_save_game1_activate (widget):
        ionest.saveGame (gameDic[gamewidget.cur_gmwidg()])
        
    def on_save_game_as1_activate (widget):
        ionest.saveGameAs (gameDic[gamewidget.cur_gmwidg()])
    
    def on_properties1_activate (widget):
        gamemodel = gameDic[gamewidget.cur_gmwidg()]
        window["event_entry"].set_text(gamemodel["Event"])
        window["site_entry"].set_text(gamemodel["Site"])
        window["round_spinbutton"].set_value(gamemodel["Round"])
        
        # Notice: GtkCalender month goes from 0 to 11, but gamemodel goes from
        # 1 to 12
        window["game_info_calendar"].clear_marks()
        window["game_info_calendar"].select_month(
                                        gamemodel["Month"]-1, gamemodel["Year"])
        window["game_info_calendar"].select_day(gamemodel["Day"])
        
        window["game_info"].show()
        
        def hide_window(button, *args):
            window["game_info"].hide()
            return True
        
        def accept_new_properties(button, *args):
            gamemodel = gameDic[gamewidget.cur_gmwidg()]
            gamemodel["Event"] = window["event_entry"].get_text()
            gamemodel["Site"] = window["site_entry"].get_text()
            gamemodel["Round"] = window["round_spinbutton"].get_value()
            gamemodel["Year"] = window["game_info_calendar"].get_date()[0]
            gamemodel["Month"] = window["game_info_calendar"].get_date()[1] + 1
            gamemodel["Day"] = window["game_info_calendar"].get_date()[2]
            window["game_info"].hide()
            return True
        
        window["game_info"].connect("delete-event", hide_window)
        window["game_info_cancel_button"].connect("clicked", hide_window)
        window["game_info_ok_button"].connect("clicked", accept_new_properties)
    
    def on_close1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        ionest.closeGame(gmwidg, gameDic[gmwidg])
    
    def on_quit1_activate (widget, *args):
        if ionest.closeAllGames (gameDic.values()) == gtk.RESPONSE_OK:
            gtk.main_quit()
        else: return True
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].view.fromWhite = \
            not gmwidg.widgets["board"].view.fromWhite
    
    def on_side_panel1_activate (widget):
        gamewidget.show_side_panel(widget.get_active())
    
    def on_show_cords_activate (widget):
        for gmwidg in gameDic.keys():
            gmwidg.widgets["board"].view.showCords = widget.get_active()
    
    def on_about1_activate (widget):
        window["aboutdialog1"].show()
    
    def on_log_viewer1_activate (widget):
        if widget.get_active():
            LogDialog.show()
        else: LogDialog.hide()
    
    def on_hint_mode_activate (widget):
        for gmwidg in gameDic.keys():
            setMode(gmwidg, HINT, widget.get_active())
    
    def on_spy_mode_activate (widget):
        for gmwidg in gameDic.keys():
            setMode(gmwidg, SPY, widget.get_active())
    
    #          Action menu          #
    
    def on_call_flag_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_call_flag_activate (widget)

    def on_draw_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_draw_activate (widget)
        
    def on_resign_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_resign_activate (widget)

    def on_force_to_move_activate (widget):
        if len(gameDic):
            gameDic[gamewidget.cur_gmwidg()].activePlayer.hurry()
    
    #          Settings menu          #
    
    def on_preferences_activate (widget):
        preferencesDialog.run()
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        window["notebook3"].set_current_page(page_num)
        
TARGET_TYPE_URI_LIST = 80
dnd_list = [ ( 'text/plain', 0, TARGET_TYPE_URI_LIST ) ]
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

class PyChess:
    def __init__(self):
        self.initGlade()
        
    def mainWindowSize (self, window):
        def savePosition ():
            myconf.set("window_width", window.get_allocation().width)
            myconf.set("window_height", window.get_allocation().height)
        atexit.register( savePosition)
        width = myconf.get("window_width")
        height = myconf.get("window_height")
        if width and height:
            window.resize(width, height)
    
    def initGlade(self):
        global window
        window = self
    
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML(prefix("glade/PyChess.glade"))
        
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        self["window1"].show_all()
        
        makeLogDialogReady()
        makeAboutDialogReady()
        gamewidget.set_widgets(self)
        ionest.handler.connect("game_started",
            GladeHandlers.__dict__["on_game_started"])
        ionest.handler.connect("game_closed",
            GladeHandlers.__dict__["on_game_closed"])
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        window["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        window["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        
        self.mainWindowSize(self["window1"])
        
        #TODO: disabled by default
        #TipOfTheDay.TipOfTheDay()
    
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        return Background()

def run ():
    PyChess()
    import signal
    signal.signal(signal.SIGINT, gtk.main_quit)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    gtk.gdk.threads_init()
    gtk.main()
