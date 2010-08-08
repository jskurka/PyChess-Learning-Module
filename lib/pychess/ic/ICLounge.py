# -*- coding: utf-8 -*-

from cStringIO import StringIO
from time import strftime, localtime, time
from math import e
from operator import attrgetter
from itertools import groupby

import gtk, pango
from gtk.gdk import pixbuf_new_from_file
from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System import conf, glock, uistuff
from pychess.System.GtkWorker import Publisher
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.System.Log import log
from pychess.widgets import ionest
from pychess.widgets.ChatWindow import ChatWindow
from pychess.widgets.SpotGraph import SpotGraph
from pychess.widgets.ChainVBox import ChainVBox
from pychess.Utils.const import *
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Players.Human import Human
from pychess.Savers import pgn, fen
from pychess.Variants import variants
from pychess.Variants.normal import NormalChess

from ICGameModel import ICGameModel
from pychess.Utils.Rating import Rating

class ICLounge (GObject):
    __gsignals__ = {
        'logout'        : (SIGNAL_RUN_FIRST, None, ()),
        'autoLogout'    : (SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, c):
        GObject.__init__(self)
        self.connection = c
        self.widgets = w = uistuff.GladeWidgets("fics_lounge.glade")
        uistuff.keepWindowSize("fics_lounge", self.widgets["fics_lounge"])

        def on_window_delete (window, event):
            self.close()
            self.emit("logout")
            return True
        self.widgets["fics_lounge"].connect("delete-event", on_window_delete)
        def on_logoffButton_clicked (button):
            self.close()
            self.emit("logout")
        self.widgets["logoffButton"].connect("clicked", on_logoffButton_clicked)        
        def on_autoLogout (alm):
            self.close()
            self.emit("autoLogout")
        self.connection.alm.connect("logOut", on_autoLogout)
        self.connection.connect("disconnected", lambda connection: self.close())
        self.connection.connect("error", lambda connection: self.close())

        global sections
        sections = (
            VariousSection(w,c),
            UserInfoSection(w,c),
            NewsSection(w,c),

            SeekTabSection(w,c),
            ChallengeTabSection(w,c),
            SeekGraphSection(w,c),
            PlayerTabSection(w,c),
            GameTabSection(w,c),
            AdjournedTabSection(w,c),

            ChatWindow(w,c),
            #ConsoleWindow(w,c),

            SeekChallengeSection(w,c),
            
            # This is not really a section. It handles error messages which
            # don't correspond to a running game
            ErrorMessages(w,c),
            
            # This is not really a section. Merely a pair of BoardManager connects
            # which takes care of ionest and stuff when a new game is started or
            # observed
            CreatedBoards(w,c)
        )

    def show (self):
        self.widgets["fics_lounge"].show()

    def present (self):
        self.widgets["fics_lounge"].present()

    def close (self):
        if self.widgets != None:
            self.widgets["fics_lounge"].hide()
        global sections
        if 'sections' in globals() and sections != None:
            for i in range(len(sections)):
                if hasattr(sections[i], "__del__"):
                    sections[i].__del__()
        sections = None
        if self.connection != None:
            self.connection.disconnect()
        self.connection = None
        self.widgets = None
#        import objgraph
#        objgraph.show_refs(self)

################################################################################
# Initialize Sections                                                          #
################################################################################

class Section:
    pass

############################################################################
# Initialize Various smaller sections                                      #
############################################################################

class VariousSection(Section):
    def __init__ (self, widgets, connection):
        #sizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        #sizeGroup.add_widget(widgets["show_chat_label"])
        #sizeGroup.add_widget(widgets["show_console_label"])
        #sizeGroup.add_widget(widgets["log_off_label"])

        connection.em.connect("onCommandNotFound", lambda em, cmd:
                log.error("Fics answered '%s': Command not found" % cmd))

############################################################################
# Initialize User Information Section                                      #
############################################################################

class UserInfoSection(Section):

    def __init__ (self, widgets, connection):
        self.widgets = widgets
        self.connection = connection
        self.pinger = None

        self.dock = self.widgets["fingerTableDock"]

        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        self.connection.bm.connect("curGameEnded", lambda *args:
                self.connection.fm.finger(self.connection.getUsername()))

        self.widgets["usernameLabel"].set_markup(
                "<b>%s</b>" % self.connection.getUsername())

    def __del__ (self):
        if self.pinger != None:
            self.pinger.stop()

    def onFinger (self, fm, finger):
        if finger.getName().lower() != self.connection.getUsername().lower():
            print finger.getName(), self.connection.getUsername()
            return
        glock.acquire()
        try:
            rows = 1
            if finger.getRating(): rows += len(finger.getRating())+1
            if finger.getEmail(): rows += 1
            if finger.getCreated(): rows += 1

            table = gtk.Table(6, rows)
            table.props.column_spacing = 12
            table.props.row_spacing = 4

            def label(value, xalign=0):
                if type(value) == float:
                    value = str(int(value))
                label = gtk.Label(value)
                label.props.xalign = xalign
                return label

            row = 0

            if finger.getRating():
                for i, item in enumerate((_("Rating"), _("Win"), _("Draw"), _("Loss"))):
                    table.attach(label(item, xalign=1), i+1,i+2,0,1)
                row += 1

                for type_, rating in finger.getRating().iteritems():
                    table.attach(label(typeName[type_]+":"), 0, 1, row, row+1)
                    table.attach(label(rating.elo, xalign=1), 1, 2, row, row+1)
                    table.attach(label(rating.wins, xalign=1), 2, 3, row, row+1)
                    table.attach(label(rating.draws, xalign=1), 3, 4, row, row+1)
                    table.attach(label(rating.losses, xalign=1), 4, 5, row, row+1)
                    row += 1

                table.attach(gtk.HSeparator(), 0, 6, row, row+1, ypadding=2)
                row += 1

            if finger.getEmail():
                table.attach(label(_("Email")+":"), 0, 1, row, row+1)
                table.attach(label(finger.getEmail()), 1, 6, row, row+1)
                row += 1

            if finger.getCreated():
                table.attach(label(_("Spent")+":"), 0, 1, row, row+1)
                s = strftime("%Y %B %d ", localtime(time()))
                s += _("online in total")
                table.attach(label(s), 1, 6, row, row+1)
                row += 1

            table.attach(label(_("Ping")+":"), 0, 1, row, row+1)
            pingLabel = gtk.Label(_("Connecting")+"...")
            pingLabel.props.xalign = 0
            self.pinger = pinger = Pinger("freechess.org")
            def callback (pinger, pingtime):
                if type(pingtime) == str:
                    pingLabel.set_text(pingtime)
                elif pingtime == -1:
                    pingLabel.set_text(_("Unknown"))
                else: pingLabel.set_text("%.0f ms" % pingtime)
            pinger.connect("recieved", callback)
            pinger.connect("error", callback)
            pinger.start()
            table.attach(pingLabel, 1, 6, row, row+1)
            row += 1

            if not self.connection.isRegistred():
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games will be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                label0.props.width_request = 300
                vbox.add(label0)
                eventbox = uistuff.initLabelLinks(_("Register now"),
                        "http://www.freechess.org/Register/index.html")
                vbox.add(eventbox)

            if self.dock.get_children():
                self.dock.remove(self.dock.get_children()[0])
            self.dock.add(table)
            self.dock.show_all()
        finally:
            glock.release()

############################################################################
# Initialize News Section                                                  #
############################################################################

class NewsSection(Section):

    def __init__(self, widgets, connection):
        self.widgets = widgets
        connection.nm.connect("readNews", self.onNewsItem)

    def onNewsItem (self, nm, news):
        glock.acquire()
        try:
            weekday, month, day, title, details = news

            dtitle = "%s, %s %s: %s" % (weekday, month, day, title)
            label = gtk.Label(dtitle)
            label.props.width_request = 300
            label.props.xalign = 0
            label.set_ellipsize(pango.ELLIPSIZE_END)
            expander = gtk.Expander()
            expander.set_label_widget(label)
            gtk.Tooltips().set_tip(expander, title)

            textview = gtk.TextView ()
            textview.set_wrap_mode (gtk.WRAP_WORD)
            textview.set_editable (False)
            textview.set_cursor_visible (False)
            textview.props.pixels_above_lines = 4
            textview.props.pixels_below_lines = 4
            textview.props.right_margin = 2
            textview.props.left_margin = 6
            uistuff.initTexviewLinks(textview, details)

            alignment = gtk.Alignment()
            alignment.set_padding(3, 6, 12, 0)
            alignment.props.xscale = 1
            alignment.add(textview)

            expander.add(alignment)
            expander.show_all()
            self.widgets["newsVBox"].pack_end(expander)
        finally:
            glock.release()

############################################################################
# Initialize Lists                                                         #
############################################################################

class ParrentListSection (Section):
    """ Parrent for sections mainly consisting of a large treeview """
    def __init__ (self):
        def updateLists (queuedCalls):
            for task in queuedCalls:
                func = task[0]
                func(*task[1:])
        self.listPublisher = Publisher(updateLists, Publisher.SEND_LIST)
        self.listPublisher.start()

    def addColumns (self, treeview, *columns, **keyargs):
        if "hide" in keyargs: hide = keyargs["hide"]
        else: hide = []
        if "pix" in keyargs: pix = keyargs["pix"]
        else: pix = []
        for i, name in enumerate(columns):
            if i in hide: continue
            if i in pix:
                crp = gtk.CellRendererPixbuf()
                crp.props.xalign = .5
                column = gtk.TreeViewColumn(name, crp, pixbuf=i)
            else:
                crt = gtk.CellRendererText()
                column = gtk.TreeViewColumn(name, crt, text=i)
                column.set_sort_column_id(i)
                column.set_resizable(True)

            column.set_reorderable(True)
            treeview.append_column(column)

    def lowLeftSearchPosFunc (self, tv, search_dialog):
        x = tv.allocation.x + tv.get_toplevel().window.get_position()[0]
        y = tv.allocation.y + tv.get_toplevel().window.get_position()[1] + \
            tv.allocation.height
        search_dialog.move(x, y)
        search_dialog.show_all()

    def pixCompareFunction (self, treemodel, iter0, iter1, column):
        pix0 = treemodel.get_value(iter0, column)
        pix1 = treemodel.get_value(iter1, column)
        if type(pix0) == gtk.gdk.Pixbuf and type(pix1) == gtk.gdk.Pixbuf:
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)
    
    def timeCompareFunction (self, treemodel, iter0, iter1, column):
        (minute0, minute1) = (treemodel.get_value(iter0, 7), treemodel.get_value(iter1, 7))
        return cmp(minute0, minute1)



########################################################################
# Initialize Seek List                                                 #
########################################################################

class SeekTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.seeks = {}

        self.seekPix = pixbuf_new_from_file(addDataPrefix("glade/seek.png"))
        self.manSeekPix = pixbuf_new_from_file(addDataPrefix("glade/manseek.png"))
        
        self.tv = self.widgets["seektreeview"]
        self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, int, str, str, str, float, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, "GameNo", "", _("Name"), _("Rating"), _("Rated"),
                         _("Type"), _("Clock"), "", "", hide=[0,7,8], pix=[1] )
        self.tv.set_search_column(2)
        for i in range(2,7):
            self.tv.get_model().set_sort_func(i, self.compareFunction, i)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        for n in range(1,6):
            column = self.tv.get_column(n)
            for cellrenderer in column.get_cell_renderers():
                column.add_attribute(cellrenderer, "foreground", 8)
        self.selection = self.tv.get_selection()
        self.lastSeekSelected = None
        self.selection.set_select_function(self.selectFunction, full=True)
        self.selection.connect("changed", self.onSelectionChanged)
        self.widgets["clearSeeksButton"].connect("clicked", self.onClearSeeksClicked)
        self.widgets["acceptButton"].connect("clicked", self.onAcceptClicked)
        self.tv.connect("row-activated", self.row_activated)
        
        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onAddSeek, seek)) )
        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onRemoveSeek, gameno)) )
        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onClearSeeks,)) )
        self.connection.bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )
        self.connection.bm.connect("curGameEnded", lambda bm, gameno, wname, bname, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )
        
    def selectFunction (self, selection, model, path, is_selected):
        if model[path][8] == "grey": return False
        else: return True
    
    def compareFunction (self, model, iter0, iter1, column):
        gameno0 = model.get_value(iter0, 0)
        gameno1 = model.get_value(iter1, 0)
        textcolor0 = model.get_value(iter0, 8)
        textcolor1 = model.get_value(iter1, 8)
        is_ascending = True if self.tv.get_column(column-1).get_sort_order() is \
                               gtk.SORT_ASCENDING else False
        if (gameno0 is not None and gameno0.startswith("C")) or (textcolor0 == "grey"):
            if is_ascending: return -1
            else: return 1
        elif (gameno1 is not None and gameno1.startswith("C")) or (textcolor1 == "grey"):
            if is_ascending: return 1
            else: return -1
        elif column is 6:
            return self.timeCompareFunction(model, iter0, iter1, column)
        else:
            value0 = model.get_value(iter0, column)
            value0 = value0.lower() if isinstance(value0, str) else value0
            value1 = model.get_value(iter1, column)
            value1 = value1.lower() if isinstance(value1, str) else value1
            return cmp(value0, value1)
        
    def onAddSeek (self, seek):
        time = _("%(min)s min") % {'min': seek["t"]}
        if seek["i"] != "0":
            time += _(" + %(sec)s sec") % {'sec': seek["i"]}
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        pix = seek["manual"] and self.manSeekPix or self.seekPix
        textcolor = "grey" if seek["w"] == self.connection.getUsername() else "black"
        ti = self.store.append ([seek["gameno"], pix, seek["w"],
                                int(seek["rt"]), rated, seek["tp"], time,
                                float(seek["t"] + "." + seek["i"]), textcolor])
        if textcolor == "grey":
            self.tv.scroll_to_cell(self.store.get_path(ti))
            self.widgets["clearSeeksButton"].set_sensitive(True)
        self.seeks [seek["gameno"]] = ti
        count = len(self.seeks)
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))

    def onRemoveSeek (self, gameno):
        if not gameno in self.seeks:
            # We ignore removes we haven't added, as it seams fics sends a
            # lot of removes for games it has never told us about
            return
        treeiter = self.seeks [gameno]
        if not self.store.iter_is_valid(treeiter):
            return
        self.store.remove (treeiter)
        del self.seeks[gameno]
        count = len(self.seeks)
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))

    def onClearSeeks (self):
        self.store.clear()
        self.seeks = {}
        self.widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))

    def onAcceptClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        gameno = model.get_value(iter, 0)
        if gameno.startswith("C"):
            self.connection.om.acceptIndex(gameno[1:])
        else:
            self.connection.om.playIndex(gameno)

    def onClearSeeksClicked (self, button):
        print >> self.connection.client, "unseek"
        self.widgets["clearSeeksButton"].set_sensitive(False)
    
    def row_activated (self, treeview, path, view_column):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        gameno = model.get_value(iter, 0)
        if gameno != self.lastSeekSelected: return
        if path != model.get_path(iter): return
        self.onAcceptClicked(None)

    def onSelectionChanged (self, selection):
        model, iter = self.widgets["seektreeview"].get_selection().get_selected()
        if iter == None: return
        self.lastSeekSelected = model.get_value(iter, 0)

    def onPlayingGame (self):
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["challengeExpander"].set_sensitive(False)
        self.widgets["clearSeeksButton"].set_sensitive(False)
        self.store.clear()
        self.widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))

    def onCurGameEnded (self):
        self.widgets["seekListContent"].set_sensitive(True)
        self.widgets["challengeExpander"].set_sensitive(True)
        self.connection.glm.refreshSeeks()

########################################################################
# Initialize Challenge List                                            #
########################################################################

class ChallengeTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.challenges = {}

        self.store = self.widgets["seektreeview"].get_model().get_model()
        self.chaPix = pixbuf_new_from_file(addDataPrefix("glade/challenge.png"))

        self.connection.om.connect("onChallengeAdd", lambda om, index, match:
                self.listPublisher.put((self.onChallengeAdd, index, match)) )

        self.connection.om.connect("onChallengeRemove", lambda om, index:
                self.listPublisher.put((self.onChallengeRemove, index)) )

    def onChallengeAdd (self, index, match):
        time = _("%(min)s min") % {'min': match["t"]}
        if match["i"] != "0":
            time += _(" + %(sec)s sec") % {'sec': match["i"]}
        rated = match["r"] == "u" and _("Unrated") or _("Rated")
        ti = self.store.prepend (["C"+index, self.chaPix, match["w"],
                                int(match["rt"]), rated, match["tp"], time,
                                float(match["t"] + "." + match["i"]), "black"])
        self.challenges [index] = ti
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        self.widgets["seektreeview"].scroll_to_cell(self.store.get_path(ti))

    def onChallengeRemove (self, index):
        if not index in self.challenges: return
        ti = self.challenges [index]
        if not self.store.iter_is_valid(ti): return
        self.store.remove (ti)
        del self.challenges [index]
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))

########################################################################
# Initialize Seek Graph                                                #
########################################################################

YMARKS = (800, 1600, 2400)
YLOCATION = lambda y: min(y/3000.,3000)
XMARKS = (5, 15)
XLOCATION = lambda x: e**(-6.579/(x+1))

# This is used to convert increment time to minutes. With a GAME_LENGTH on
# 40, a game on two minutes and twelve secconds will be placed at the same
# X location as a game on 2+12*40/60 = 10 minutes
GAME_LENGTH = 40

class SeekGraphSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.graph = SpotGraph()

        for rating in YMARKS:
            self.graph.addYMark(YLOCATION(rating), str(rating))
        for mins in XMARKS:
            self.graph.addXMark(XLOCATION(mins), str(mins) + _(" min"))

        self.widgets["graphDock"].add(self.graph)
        self.graph.show()

        self.graph.connect("spotClicked", self.onSpotClicked)

        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onSeekAdd, seek)) )

        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onSeekRemove, gameno)) )

        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onSeekClear,)) )

        self.connection.bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )

        self.connection.bm.connect("curGameEnded", lambda bm, gameno, wname, bname, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )

    def onSpotClicked (self, graph, name):
        self.connection.bm.play(name)

    def onSeekAdd (self, seek):
        x = XLOCATION (float(seek["t"]) + float(seek["i"]) * GAME_LENGTH/60.)
        y = seek["rt"].isdigit() and YLOCATION(float(seek["rt"])) or 0
        type = seek["r"] == "u" and 1 or 0

        text = "%s (%s)" % (seek["w"], seek["rt"])
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        text += "\n%s %s" % (rated, seek["tp"])
        text += "\n" + _("%(min)s min + %(sec)s sec") % {'min': seek["t"], 'sec': seek["i"]}

        self.graph.addSpot(seek["gameno"], text, x, y, type)

    def onSeekRemove (self, gameno):
        self.graph.removeSpot(gameno)

    def onSeekClear (self):
        self.graph.clearSpots()

    def onPlayingGame (self):
        self.widgets["seekGraphContent"].set_sensitive(False)
        self.graph.clearSpots()

    def onCurGameEnded (self):
        self.widgets["seekGraphContent"].set_sensitive(True)

########################################################################
# Initialize Players List                                              #
########################################################################

class PlayerTabSection (ParrentListSection):

    peoplepix = load_icon(15, "stock_people", "system-users")
    bookpix = load_icon(15, "stock_book_blue", "accessories-dictionary")
    easypix = load_icon(15, "weather-few-clouds")
    advpix = load_icon(15, "weather-overcast")
    exppix = load_icon(15, "weather-storm")
    cmppix = load_icon(15, "stock_notebook", "computer")

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.players = {}

        self.tv = self.widgets["playertreeview"]
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, int)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns(self.tv, "", _("Name"), _("Rating"), pix=[0])
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 0)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass

        self.connection.glm.connect("addPlayer", lambda glm, player:
                self.listPublisher.put((self.onPlayerAdd, player)) )

        self.connection.glm.connect("removePlayer", lambda glm, name:
                self.listPublisher.put((self.onPlayerRemove, name)) )

        self.widgets["private_chat_button"].connect("clicked", self.onPrivateChatClicked)
        self.widgets["private_chat_button"].set_sensitive(False)
        self.tv.get_selection().connect_after("changed", self.onSelectionChanged)

    def onPlayerAdd (self, player):
        if player["name"] in self.players: return
        rating = player["rating"]
        title = player["title"]
        if title & 0x02:
            title = PlayerTabSection.cmppix
        elif not rating:
            title = PlayerTabSection.peoplepix
        else:
            if rating < 1300:
                title = PlayerTabSection.easypix
            elif rating < 1600:
                title = PlayerTabSection.advpix
            else:
                title = PlayerTabSection.exppix
        #else:
        #    # Admins gets a book picture
        #    title = PlayerTabSection.bookpix
        ti = self.store.append ([title, player["name"], rating])
        self.players [player["name"]] = ti
        count = len(self.players)
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        self.widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))

    def onPlayerRemove (self, name):
        if not name in self.players:
            return
        ti = self.players [name]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.players[name]
        count = len(self.players)
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        self.widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))

    def onPrivateChatClicked (self, button):
        model, iter = self.widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return
        playerName = model.get_value(iter, 1)
        for section in sections:
            if isinstance(section, ChatWindow):
                section.openChatWithPlayer(playerName)
                #TODO: isadmin og type

    def onSelectionChanged (self, selection):
        isAnythingSelected = selection.get_selected()[1] != None
        self.widgets["private_chat_button"].set_sensitive(isAnythingSelected)

########################################################################
# Initialize Games List                                                #
########################################################################

class GameTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.games = {}

        self.recpix = load_icon(16, "media-record")
        self.clearpix = pixbuf_new_from_file(addDataPrefix("glade/board.png"))

        self.tv = self.widgets["gametreeview"]
        self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str, str, int)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.addColumns (
                self.tv, "GameNo", "", _("White Player"), _("Black Player"),
                _("Game Type"), "Time", hide=[0,5], pix=[1] )
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)

        def typeCompareFunction (treemodel, iter0, iter1):
            return cmp (treemodel.get_value(iter0, 5),
                        treemodel.get_value(iter1, 5))
        self.tv.get_model().set_sort_func(4, typeCompareFunction)

        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        def searchCallback (model, column, key, iter):
            if model.get_value(iter, 2).lower().startswith(key) or \
                model.get_value(iter, 3).lower().startswith(key):
                return False
            return True
        self.tv.set_search_equal_func (searchCallback)

        self.connection.glm.connect("addGame", lambda glm, game:
                self.listPublisher.put((self.onGameAdd, game)) )

        self.connection.glm.connect("removeGame", lambda glm, gameno, wname, bname, res, com:
                self.listPublisher.put((self.onGameRemove, gameno)) )

        self.connection.bm.connect("wasPrivate", lambda bm, game:
                self.listPublisher.put((self.onWasPrivate, game)) )

        self.widgets["observeButton"].connect ("clicked", self.onObserveClicked)
        self.tv.connect("row-activated", self.onObserveClicked)

        self.connection.bm.connect("observeBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onGameObserved, board)) )

        self.connection.bm.connect("obsGameUnobserved", lambda bm, gameno:
                self.listPublisher.put((self.onGameUnobserved, gameno)) )

    def onGameAdd (self, game):
        type = game["type"]

        if "min" in game:
            length = game["min"]*60 + game["inc"]*40
        elif "lightning" in type.lower():
            length = 100
        elif "blitz" in type.lower():
            length = 9*60
        else:
            length = 15*60

        if game["private"]:
            type += ", " + _("Private")

        ti = self.store.append ([game["gameno"], self.clearpix, game["wn"],
                                game["bn"], type, length])
        self.games[game["gameno"]] = ti
        count = len(self.games)
        postfix = count == 1 and _("Game Running") or _("Games Running")
        self.widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))

    def onWasPrivate (self, gameno):
        # When observable games were added to the list later than the latest
        # full send, private information will not be known.
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            if gameno == model.get_value(rowiter, 0):
                gametype = model.get_value(rowiter, 4)
                if not _("Private") in gametype:
                    gametype += ", " + _("Private")
                    childmodel = model.get_model()
                    childrowiter = model.convert_iter_to_child_iter(None, rowiter)
                    childmodel.set_value(childrowiter, 4, gametype)
                break

    def onGameRemove (self, gameno):
        if not gameno in self.games:
            return
        ti = self.games[gameno]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.games[gameno]
        count = len(self.games)
        postfix = count == 1 and _("Game Running") or _("Games Running")
        self.widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))

    def onObserveClicked (self, widget, *args):
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            gameno = model.get_value(rowiter, 0)
            self.connection.bm.observe(gameno)

    def onGameObserved (self, board):
        threeiter = self.games[board["gameno"]]
        self.store.set_value (threeiter, 1, self.recpix)

    def onGameUnobserved (self, gameno):
        if gameno in self.games:
            threeiter = self.games[gameno]
            self.store.set_value(threeiter, 1, self.clearpix)

########################################################################
# Initialize Adjourned List                                            #
########################################################################
# We skip adjourned games until Staunton

class AdjournedTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        self.connection = connection
        self.opponents = {}

        # Set up the treeview

        self.wpix = load_icon(16, "stock_draw-rounded-square-unfilled", "computer")
        self.bpix = load_icon(16, "stock_draw-rounded-square", "computer")

        self.tv = widgets["adjournedtreeview"]
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, _("Your color"), _("Opponent"),
                                  _("Is online"), _("Length"), _("Date/Time"), pix=[0])

        # Connect to adjourmentlist signals

        self.connection.adm.connect("onAdjournmentsList", lambda glm, adjournments:
                self.listPublisher.put((self.onAdjournmentsList, adjournments)) )
        self.connection.adm.queryAdjournments()

        self.connection.bm.connect("curGameEnded", lambda bm, gameno, wname, bname, result, reason:
                self.listPublisher.put((self.onCurGameEnded, result)))

        # Set up buttons

        widgets["previewButton"].connect("clicked", self.onPreviewButtonClicked)
        self.connection.adm.connect("onGamePreview", lambda adm, pgn, secs, gain, wname, bname:
                self.listPublisher.put((self.onGamePreview, pgn, secs, gain, wname, bname)))


    def onAdjournmentsList (self, adjournments):
        for adjourn in adjournments:
            if adjourn["opponent"].lower() in self.opponents:
                continue
            pix = (self.wpix, self.bpix)[adjourn["color"]]
            opstatus = adjourn["online"] and _("Online") or _("Offline")
            ti = self.store.append ([pix, adjourn["opponent"],
                                     opstatus, adjourn["length"], adjourn["time"]])
            self.opponents[adjourn["opponent"].lower()] = ti

    def onCurGameEnded (self, result):
        if result == ADJOURNED:
            self.store.clear()
            self.opponents.clear()
            self.connection.adm.queryAdjournments()

    def onPreviewButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.queryMoves(opponent)

    def onGamePreview (self, pgn, secs, gain, wname, bname):
        print pgn

        #if not connection.registered:
        #    widgets["notebook"].remove_page(4)
        #else:
        #    tv = widgets["adjournedtreeview"]
        #    astore = gtk.ListStore (str, str, str, str)
        #    tv.set_model (gtk.TreeModelSort (astore))
        #    addColumns (tv, _("Opponent"), _("Status"), _("% Played"), _("Date"))
        #
        #    def on_adjourn_add (glm, game):
        #        def call ():
        #            ti = astore.append ([game["opponent"], game["opstatus"],
        #                             "%d %%" % game["procPlayed"], game["date"]])
        #        listPublisher.put(call)
        #    glm.connect("addAdjourn", on_adjourn_add)

############################################################################
# Initialize seeking-/challengingpanel                                     #
############################################################################

RATING_SLIDER_STEP = 25
    
class SeekChallengeSection (ParrentListSection):
        
    novicepix = load_icon(15, "weather-clear")
    beginnerpix = load_icon(15, "weather-few-clouds")
    intermediatepix = load_icon(15, "weather-overcast")
    advancedpix = load_icon(15, "weather-showers")
    expertpix = load_icon(15, "weather-storm")
    
    variants = {
        SHUFFLECHESS : TYPE_WILD,
        FISCHERRANDOMCHESS : TYPE_WILD,
        RANDOMCHESS: TYPE_WILD,
        ASYMMETRICRANDOMCHESS: TYPE_WILD,
        UPSIDEDOWNCHESS : TYPE_WILD,
        PAWNSPUSHEDCHESS : TYPE_WILD,
        PAWNSPASSEDCHESS : TYPE_WILD,
        LOSERSCHESS : TYPE_LOSERS,
        PAWNODDSCHESS : TYPE_WILD,
        KNIGHTODDSCHESS : TYPE_WILD,
        ROOKODDSCHESS : TYPE_WILD,
        QUEENODDSCHESS : TYPE_WILD,
    }
    
    seekEditorWidgets = (
        "untimedCheck", "minutesSpin", "gainSpin",
        "strengthCheck", "chainAlignment", "ratingCenterSlider", "toleranceSlider", "toleranceHBox",
        "nocolorRadio", "whitecolorRadio", "blackcolorRadio",
        # variantCombo has to come before other variant widgets so that
        # when the widget is loaded, variantRadio isn't selected by the callback,
        # overwriting the user's saved value for the variant radio buttons
        "variantCombo", "noVariantRadio", "variantRadio",
        "ratedGameCheck", "manualAcceptCheck" )
    
    seekEditorWidgetDefaults = {
        "untimedCheck": [False, False, False],
        "minutesSpin": [15, 5, 2],
        "gainSpin": [10, 0, 1],
        "strengthCheck": [False, True, False],
        "chainAlignment": [True, True, True],
        "ratingCenterSlider": [40, 40, 40],
        "toleranceSlider": [8, 8, 8],
        "toleranceHBox": [False, False, False],
        "variantCombo": [RANDOMCHESS, FISCHERRANDOMCHESS, LOSERSCHESS],
        "noVariantRadio": [True, False, True],
        "variantRadio": [False, True, False],
        "nocolorRadio": [True, True, True],
        "whitecolorRadio": [False, False, False],
        "blackcolorRadio": [False, False, False],
        "ratedGameCheck": [False, True, True],
        "manualAcceptCheck": [False, False, False],
    }
    
    seekEditorWidgetGettersSetters = {}

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.finger = None
        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        
        self.widgets["untimedCheck"].connect("toggled", self.onUntimedCheckToggled)
        self.widgets["minutesSpin"].connect("value-changed", self.onTimeSpinChanged)
        self.widgets["gainSpin"].connect("value-changed", self.onTimeSpinChanged)
        self.onTimeSpinChanged(self.widgets["minutesSpin"])
        
        self.widgets["nocolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.widgets["whitecolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.widgets["blackcolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.onColorRadioChanged(self.widgets["nocolorRadio"])
        
        self.widgets["noVariantRadio"].connect("toggled", self.onVariantRadioChanged)
        self.widgets["variantRadio"].connect("toggled", self.onVariantRadioChanged)
        variantComboGetter, variantComboSetter = self.__initVariantCombo(self.widgets["variantCombo"])
        self.seekEditorWidgetGettersSetters["variantCombo"] = (variantComboGetter, variantComboSetter)
        self.widgets["variantCombo"].connect("changed", self.onVariantComboChanged)

        self.widgets["editSeekDialog"].connect("delete_event", lambda *a: True)
        glock.glock_connect(self.connection, "disconnected",
                      lambda c: self.widgets and self.widgets["editSeekDialog"].response(gtk.RESPONSE_CANCEL))

        self.widgets["strengthCheck"].connect("toggled", self.onStrengthCheckToggled)
        self.onStrengthCheckToggled(self.widgets["strengthCheck"])
        self.widgets["ratingCenterSlider"].connect("value-changed", self.onRatingCenterSliderChanged)
        self.onRatingCenterSliderChanged(self.widgets["ratingCenterSlider"])
        self.widgets["toleranceSlider"].connect("value-changed", self.onToleranceSliderChanged)
        self.onToleranceSliderChanged(self.widgets["toleranceSlider"])
        self.widgets["toleranceButton"].connect("clicked", self.onToleranceButtonClicked)
        def toleranceHBoxGetter (widget):
            return self.widgets["toleranceHBox"].get_property("visible")
        def toleranceHBoxSetter (widget, visible):
            assert type(visible) is bool
            if visible:
                self.widgets["toleranceHBox"].show()
            else:
                self.widgets["toleranceHBox"].hide()
        self.seekEditorWidgetGettersSetters["toleranceHBox"] = (toleranceHBoxGetter, toleranceHBoxSetter)
        
        self.chainbox = ChainVBox()
        self.chainbox.connect("clicked", self.onChainBoxClicked)
        self.widgets["chainAlignment"].add(self.chainbox)
        def chainboxGetter (widget):
            return self.chainbox.active
        def chainboxSetter (widget, is_active):
            self.chainbox.active = is_active
        self.seekEditorWidgetGettersSetters["chainAlignment"] = (chainboxGetter, chainboxSetter)
        
        self.widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        self.widgets["challengeButton"].connect("clicked", self.onChallengeButtonClicked)
        
        seekSelection = self.widgets["seektreeview"].get_selection()
        seekSelection.connect_after("changed", self.onSeekSelectionChanged)
        playerSelection = self.widgets["playertreeview"].get_selection()
        playerSelection.connect_after("changed", self.onPlayerSelectionChanged)
        self.onPlayerSelectionChanged(playerSelection)
        
        for widget in ("seek1Radio", "seek2Radio", "seek3Radio",
                       "challenge1Radio", "challenge2Radio", "challenge3Radio"):
            uistuff.keep(self.widgets[widget], widget)
        
        self.connections = {}
        self.lastdifference = 0
        self.savedSeekRadioTexts = [_("Blitz"), _("Blitz"), _("Blitz")]
        
        for i in range(1,4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
            self.connections["seek%sRadioConfigButton" % i] = \
                self.widgets["seek%sRadioConfigButton" % i].connect( \
                "clicked", self.onSeekRadioConfigButtonClicked, i)
            self.connections["challenge%sRadioConfigButton" % i] = \
                self.widgets["challenge%sRadioConfigButton" % i].connect( \
                "clicked", self.onChallengeRadioConfigButtonClicked, i)
        
        if not connection.isRegistred():
            self.widgets["ratedGameCheck"].set_active(False)
            self.widgets["ratedGameCheck"].hide()
        else:
            self.widgets["ratedGameCheck"].show()
        
        # TODO: if registered and no default, update default rating center
        # to be as close as possible to users blitz rating

    def onSeekButtonClicked (self, button):
        if self.widgets["seek3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["seek2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        
        min, incr, variant, ratingrange, color, rated, manual = self.__getSeekEditorDialogValues()
        self.connection.glm.seek(min, incr, rated, ratingrange, color, variant, manual)

    def onChallengeButtonClicked (self, button):
        model, iter = self.widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return
        playername = model.get_value(iter, 1)
        
        if self.widgets["challenge3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["challenge2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        
        min, incr, variant, ratingrange, color, rated, manual = self.__getSeekEditorDialogValues()
        self.connection.om.challenge(playername, min, incr, rated, color, variant)

    def onSeekRadioConfigButtonClicked (self, configimage, seeknumber): 
        self.__showSeekEditor(seeknumber)
    
    def onChallengeRadioConfigButtonClicked (self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber, challengemode=True)
        self.onPlayerSelectionChanged(self.widgets["playertreeview"].get_selection())
        
    def __showSeekEditor (self, seeknumber, challengemode=False):
        if not challengemode:
            radioname = "seek%dRadio"
            opradioname = "challenge%dRadio"
            buttonname = "seek%dRadioConfigButton"
            opbuttonname = "challenge%dRadioConfigButton"
            configbuttoncallee = self.onSeekRadioConfigButtonClicked
            self.widgets["strengthFrame"].show()
            self.widgets["manualAcceptCheck"].show()
        else:
            radioname = "challenge%dRadio"
            opradioname = "seek%dRadio"
            buttonname = "challenge%dRadioConfigButton"
            opbuttonname = "seek%dRadioConfigButton"
            configbuttoncallee = self.onChallengeRadioConfigButtonClicked
            self.widgets["strengthFrame"].hide()
            self.widgets["manualAcceptCheck"].hide()
            self.widgets["editSeekDialog"].resize(100, 100)
        
        self.widgets["chainAlignment"].show_all()        
        self.__loadSeekEditor(seeknumber)
        configbutton = buttonname % seeknumber
        
        def onResponse (dialog, response):
            self.widgets["editSeekDialog"].hide()
            self.widgets["editSeekDialog"].disconnect(handlerId)
            for i in range(1,4):
                self.widgets[buttonname % i].set_sensitive(True)
                self.widgets[opbuttonname % i].set_sensitive(True)
            if configbutton in self.connections:
                self.widgets[configbutton].disconnect(self.connections[configbutton])
            self.connections[configbutton] = \
               self.widgets[configbutton].connect("clicked", configbuttoncallee, seeknumber)
            if response != gtk.RESPONSE_OK:
                return
            self.__saveSeekEditor(seeknumber)
            self.__writeSavedSeeks(seeknumber)
        
        for i in range(1,4):
            if i is not seeknumber:
                self.widgets[buttonname % i].set_sensitive(False)
            self.widgets[opbuttonname % i].set_sensitive(False)
        if configbutton in self.connections:
            self.widgets[configbutton].disconnect(self.connections[configbutton])
        self.connections[configbutton] = \
           self.widgets[configbutton].connect("clicked", lambda *w: self.widgets["editSeekDialog"].present())
        self.widgets[radioname % seeknumber].set_active(True)
        self.widgets[opradioname % seeknumber].set_active(True)
        
        self.__updateYourRatingHBox()
        self.__updateRatingCenterInfoBox()
        self.__updateToleranceButton()
        self.onUntimedCheckToggled(self.widgets["untimedCheck"])
        
        handlerId = self.widgets["editSeekDialog"].connect("response", onResponse)
        title = "Edit Seek: " + self.widgets[radioname % seeknumber].get_label()[:-1]
        self.widgets["editSeekDialog"].set_title(title)
        self.widgets["editSeekDialog"].show()
    
    def onSeekSelectionChanged (self, selection):
        # You can't press "Accept" button when nobody are selected
        isAnythingSelected = selection.get_selected()[1] != None
        self.widgets["acceptButton"].set_sensitive(isAnythingSelected)
    
    def onPlayerSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        
        # You can't press challengebutton when nobody is selected
        isAnythingSelected = iter != None
        self.widgets["challengeButton"].set_sensitive(isAnythingSelected)
        
        if isAnythingSelected:
            # You can't challenge a guest to a rated game
            playerTitle = model.get_value(iter, 0)
            isGuestPlayer = playerTitle == PlayerTabSection.peoplepix
        self.widgets["ratedGameCheck"].set_sensitive(not isAnythingSelected or not isGuestPlayer)

    #-------------------------------------------------------- Seek Editor
        
    def __writeSavedSeeks (self, seekNumber):
        """ Writes saved seek strings for both the Seek Panel and the Challenge Panel """
        min, gain, variant, ratingRange, color, rated, manual = self.__getSeekEditorDialogValues()
        isUntimedGame = True if min is 0 else False
        radioText = self.__getNameOfTimeControl(min, gain)
        self.savedSeekRadioTexts[seekNumber-1] = radioText
        self.__writeSeekRadioLabels()
        seek = []
        challenge = []
        
        if isUntimedGame:
            pass
        elif gain > 0:
            seek.append("%d min + %d sec/move" % (min, gain))
            challenge.append("%d min + %d sec/move" % (min, gain))
        else:
            seek.append("%d min" % (min))
            challenge.append("%d min" % (min))
        
        if variant != NORMALCHESS and not isUntimedGame:
            seek.append("%s" % variants[variant].name)
            challenge.append("%s" % variants[variant].name)
        
        if ratingRange[0] > 0:
            ratingText = "%d" % ratingRange[0]
            if ratingRange[1] == 9999:
                ratingText += "↑"
            else:
                ratingText += "-%d" % ratingRange[1]
            seek.append(ratingText)
        elif ratingRange[1] != 9999:
            seek.append("%d↓" % ratingRange[1])
        
        if color == WHITE:
            seek.append(_("White"))
            challenge.append(_("White"))
        elif color == BLACK:
            seek.append(_("Black"))
            challenge.append(_("Black"))
        
        if rated and not isUntimedGame:
            seek.append(_("Rated"))
            challenge.append(_("Rated"))
        
        if manual:
            seek.append(_("Manual"))
        
        seekText = ", ".join(seek)
        challengeText = ", ".join(challenge)
        if seekNumber == 1:
            self.widgets["seek1RadioLabel"].set_text(seekText)
            self.widgets["challenge1RadioLabel"].set_text(challengeText)
        elif seekNumber == 2:
            self.widgets["seek2RadioLabel"].set_text(seekText)
            self.widgets["challenge2RadioLabel"].set_text(challengeText)
        else:
            self.widgets["seek3RadioLabel"].set_text(seekText)
            self.widgets["challenge3RadioLabel"].set_text(challengeText)
        
    def __loadSeekEditor (self, seeknumber):
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber,
                                   get_value_=self.seekEditorWidgetGettersSetters[widget][0],
                                   set_value_=self.seekEditorWidgetGettersSetters[widget][1],
                                   first_value=self.seekEditorWidgetDefaults[widget][seeknumber-1])
            elif widget in self.seekEditorWidgetDefaults:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber,
                                   first_value=self.seekEditorWidgetDefaults[widget][seeknumber-1])
            else:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber)
        
        self.lastdifference = conf.get("lastdifference-%d" % seeknumber, -1)
        
    def __saveSeekEditor (self, seeknumber):
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.saveDialogWidget(self.widgets[widget], widget, seeknumber,
                                         get_value_=self.seekEditorWidgetGettersSetters[widget][0])
            else:
                uistuff.saveDialogWidget(self.widgets[widget], widget, seeknumber)
        
        conf.set("lastdifference-%d" % seeknumber, self.lastdifference)

    def __getSeekEditorDialogValues (self):
        if self.widgets["untimedCheck"].get_active():
            min = 0
            incr = 0
        else:
            min = int(self.widgets["minutesSpin"].get_value())
            incr = int(self.widgets["gainSpin"].get_value())
        
        if self.widgets["strengthCheck"].get_active():
            ratingrange = [0, 9999]
        else:
            center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
            tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
            minrating = center - tolerance
            minrating = minrating > 0 and minrating or 0
            maxrating = center + tolerance
            maxrating = maxrating >= 3000 and 9999 or maxrating 
            ratingrange = [minrating, maxrating]
        
        if self.widgets["nocolorRadio"].get_active():
            color = None
        elif self.widgets["whitecolorRadio"].get_active():
            color = WHITE
        else:
            color = BLACK

        if self.widgets["noVariantRadio"].get_active() or \
           self.widgets["untimedCheck"].get_active():
            variant = NORMALCHESS
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters["variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])

        rated = self.widgets["ratedGameCheck"].get_active() and \
                   not self.widgets["untimedCheck"].get_active()
        manual = self.widgets["manualAcceptCheck"].get_active()
        
        return min, incr, variant, ratingrange, color, rated, manual
    
    def __getTypeOfTimeControl (self, minutes, gain):
        assert type(minutes) == int and type(gain) == int
        assert minutes >= 0 and gain >= 0
        gainminutes = gain > 0 and (gain*60)-1 or 0
        if minutes is 0:
            return TYPE_UNTIMED
        elif (minutes*60) + gainminutes >= (15*60):
            return TYPE_STANDARD
        elif (minutes*60) + gainminutes >= (3*60):
            return TYPE_BLITZ
        else:
            return TYPE_LIGHTNING
        
    def __getNameOfTimeControl (self, minutes, gain):
        time_control = self.__getTypeOfTimeControl(minutes, gain)
        if time_control is TYPE_UNTIMED:
            return _("Untimed")
        elif time_control is TYPE_STANDARD:
            return _("Standard")
        elif time_control is TYPE_BLITZ:
            return _("Blitz")
        else:
            return _("Lightning")
        
    def __writeSeekRadioLabels (self):
        gameTypes = { _("Untimed"): [0, 1], _("Standard"): [0, 1],
                      _("Blitz"): [0, 1], _("Lightning"): [0, 1] }
        
        for i in range(3):
            gameTypes[self.savedSeekRadioTexts[i]][0] += 1
        for i in range(3):
            if gameTypes[self.savedSeekRadioTexts[i]][0] > 1:
                labelText = "%s #%d:" % \
                   (self.savedSeekRadioTexts[i], gameTypes[self.savedSeekRadioTexts[i]][1])
                self.widgets["seek%dRadio" % (i+1)].set_label(labelText)
                self.widgets["challenge%dRadio" % (i+1)].set_label(labelText)
                gameTypes[self.savedSeekRadioTexts[i]][1] += 1
            else:
                self.widgets["seek%dRadio" % (i+1)].set_label(self.savedSeekRadioTexts[i]+":")
                self.widgets["challenge%dRadio" % (i+1)].set_label(self.savedSeekRadioTexts[i]+":")

    def __getPixbufForRating (self, rating):
        assert type(rating) == int, "rating not an int: %s" % str(rating)
        if rating >= 1900:
            return self.expertpix
        elif rating >= 1600:
            return self.advancedpix
        elif rating >= 1300:
            return self.intermediatepix
        elif rating >= 1000:
            return self.beginnerpix
        else:
            return self.novicepix
        
    def __updateRatingRangeBox (self):
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
        minRating = center - tolerance
        minRating = minRating > 0 and minRating or 0
        maxRating = center + tolerance
        maxRating = maxRating >= 3000 and 9999 or maxRating 
        
        self.widgets["ratingRangeMinLabel"].set_label("%d" % minRating)
        self.widgets["ratingRangeMaxLabel"].set_label("%d" % maxRating)
        
        for widgetName, rating in (("ratingRangeMinImage", minRating),
                                   ("ratingRangeMaxImage", maxRating)):
            pixbuf = self.__getPixbufForRating(rating)
            self.widgets[widgetName].set_from_pixbuf(pixbuf)
        
        self.widgets["ratingRangeMinImage"].show()
        self.widgets["ratingRangeMinLabel"].show()
        self.widgets["dashLabel"].show()        
        self.widgets["ratingRangeMaxImage"].show()
        self.widgets["ratingRangeMaxLabel"].show()
        if minRating == 0:
            self.widgets["ratingRangeMinImage"].hide()
            self.widgets["ratingRangeMinLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMaxLabel"].set_label("%d↓" % maxRating)
        if maxRating == 9999:
            self.widgets["ratingRangeMaxImage"].hide()
            self.widgets["ratingRangeMaxLabel"].hide()
            self.widgets["dashLabel"].hide()            
            self.widgets["ratingRangeMinLabel"].set_label("%d↑" % minRating)
        if minRating == 0 and maxRating == 9999:
            self.widgets["ratingRangeMinLabel"].set_label("Any strength")
            self.widgets["ratingRangeMinLabel"].show()
    
    def __getGameTypes (self):
        if self.widgets["untimedCheck"].get_active():
            gametype = self.__getNameOfTimeControl(0, 0)
            ratingtype = self.__getTypeOfTimeControl(0, 0)
        elif self.widgets["noVariantRadio"].get_active():
            min = int(self.widgets["minutesSpin"].get_value())
            gain = int(self.widgets["gainSpin"].get_value())
            gametype = self.__getNameOfTimeControl(min, gain)
            ratingtype = self.__getTypeOfTimeControl(min, gain)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters["variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = variants[variant].name
            ratingtype = self.variants[variant]
        return gametype, ratingtype
        
    def __updateYourRatingHBox (self):
        if self.finger == None: return
        gametype, ratingtype = self.__getGameTypes()
        
        self.widgets["yourRatingNameLabel"].set_label(gametype)
        try:
            rating = self.finger.getRating(type=ratingtype)
        except KeyError:  # the user doesn't have a rating for this game type
            self.widgets["yourRatingImage"].clear()
            self.widgets["yourRatingLabel"].set_label(_("Unrated"))
            return
        rating = int(rating.elo)
        pixbuf = self.__getPixbufForRating(rating)
        self.widgets["yourRatingImage"].set_from_pixbuf(pixbuf)
        self.widgets["yourRatingLabel"].set_label(str(rating))
        
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        newclamp = self.__clamp(rating)
        difference = newclamp - center
        if self.chainbox.active and difference is not self.lastdifference:
            newsliderval = (newclamp - self.lastdifference) / RATING_SLIDER_STEP
            self.widgets["ratingCenterSlider"].set_value(newsliderval)
        else:
            self.lastdifference = difference
    
    def __clamp (self, rating):
        assert type(rating) is int
        mod = rating % RATING_SLIDER_STEP
        if mod > RATING_SLIDER_STEP / 2:
            return rating - mod + RATING_SLIDER_STEP
        else:
            return rating - mod
    
    def __initVariantCombo (self, combo):
        model = gtk.TreeStore(str)
        cellRenderer = gtk.CellRendererText()
        combo.clear()
        combo.pack_start(cellRenderer, True)
        combo.add_attribute(cellRenderer, 'text', 0)
        combo.set_model(model)
        
        groupNames = {VARIANTS_BLINDFOLD: _("Blindfold"),
                      VARIANTS_ODDS: _("Odds"),
                      VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other")}
        ficsvariants = [v for k, v in variants.iteritems() if k in self.variants.keys()]
        groups = groupby(ficsvariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            iter = model.append(None, (groupNames[id],))
            for variant in group:
                subiter = model.append(iter, (variant.name,))
                path = model.get_path(subiter)
                pathToVariant[path] = variant.board.variant
                variantToPath[variant.board.variant] = path
        
        # this stops group names (eg "Shuffle") from being displayed in submenus
        def cellFunc (combo, cell, model, iter, data):
            isChildNode = not model.iter_has_child(iter)
            cell.set_property("sensitive", isChildNode)
        combo.set_cell_data_func(cellRenderer, cellFunc, None)
        
        def comboGetter (combo):
            path = model.get_path(combo.get_active_iter())
            return pathToVariant[path]
        def comboSetter (combo, variant):
            assert variant in variants, "not a variant: \"%s\"" % str(variant)
            combo.set_active_iter(model.get_iter(variantToPath[variant]))
        return comboGetter, comboSetter
    
    # TODO: glock this!
    def onFinger (self, fm, finger):
        if not finger.getName() == self.connection.getUsername(): return
        self.finger = finger
        self.__updateYourRatingHBox()

    def onChainBoxClicked (self, chainbox):
#        if chainbox.active:
#            print "locked"
#        else:
#            print "unlocked"
        pass
    
    def onTimeSpinChanged (self, spin):
        minutes = self.widgets["minutesSpin"].get_value_as_int()
        gain = self.widgets["gainSpin"].get_value_as_int()
        name = self.__getNameOfTimeControl(minutes, gain)
        self.widgets["timeControlNameLabel"].set_label("%s" % name)
        self.__updateYourRatingHBox()
    
    def onUntimedCheckToggled (self, check):
        is_untimed_game = check.get_active()
        self.widgets["timeControlConfigVBox"].set_sensitive(not is_untimed_game)
        # on FICS, untimed games can't be rated and can't be a chess variant
        self.widgets["variantHBox"].set_sensitive(not is_untimed_game)
        self.widgets["ratedGameCheck"].set_sensitive(not is_untimed_game)
        self.__updateYourRatingHBox()
        
    def onStrengthCheckToggled (self, check):
        strengthsensitive = not check.get_active()
        self.widgets["strengthImage"].set_sensitive(strengthsensitive)
        self.widgets["strengthConfigVBox"].set_sensitive(strengthsensitive)        
        
    def onRatingCenterSliderChanged (self, slider):
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        pixbuf = self.__getPixbufForRating(center)
        self.widgets["ratingCenterLabel"].set_label("%d" % (center))
        self.widgets["ratingCenterImage"].set_from_pixbuf(pixbuf)        
        self.__updateRatingRangeBox()

        gametype, ratingtype = self.__getGameTypes()
        if self.finger == None: return
        try:
            rating = self.finger.getRating(type=ratingtype)
        except KeyError:  # the user doesn't have a rating for this game type
            return
        rating = int(rating.elo)
        newclamp = self.__clamp(rating)
        self.lastdifference = newclamp - center
        
    def __updateRatingCenterInfoBox (self):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["ratingCenterAlignment"].set_property("top-padding", 4)
            self.widgets["ratingCenterInfoHBox"].show()
        else:
            self.widgets["ratingCenterAlignment"].set_property("top-padding", 0)
            self.widgets["ratingCenterInfoHBox"].hide()
    
    def __updateToleranceButton (self):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["toleranceButton"].set_property("label", _("Hide"))
        else:
            self.widgets["toleranceButton"].set_property("label", _("Change Tolerance"))

    def onToleranceButtonClicked (self, button):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["toleranceHBox"].hide()
        else:
            self.widgets["toleranceHBox"].show()
        self.__updateToleranceButton()
        self.__updateRatingCenterInfoBox()

    def onToleranceSliderChanged (self, slider):
        tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
        self.widgets["toleranceLabel"].set_label("±%d" % tolerance)
        self.__updateRatingRangeBox()

    def onColorRadioChanged (self, radio):
        if self.widgets["nocolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-unknown.png"))
            self.widgets["colorImage"].set_sensitive(False)
        elif self.widgets["whitecolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-white.png"))
            self.widgets["colorImage"].set_sensitive(True)
        elif self.widgets["blackcolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-black.png"))
            self.widgets["colorImage"].set_sensitive(True)

    def onVariantRadioChanged (self, radio):
        self.__updateYourRatingHBox()
    
    def onVariantComboChanged (self, combo):
        self.widgets["variantRadio"].set_active(True)            
        self.__updateYourRatingHBox()

class ConsoleWindow:
    def __init__ (self, widgets, connection):
        pass

############################################################################
# Relay server error messages to the user which aren't part of a game      #
############################################################################

class ErrorMessages (Section):
    def __init__ (self, widgets, connection):
        self.connection = connection
        self.connection.bm.connect("tooManySeeks", self.tooManySeeks)
    
    @glock.glocked
    def tooManySeeks (self, om):
        title = _("You can only have 3 outstanding seeks")
        description = _("You can only have 3 outstanding seeks at the same time. If you want to add a new seek you must clear your currently active seeks. Clear your seeks?")
        d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO)
        d.set_markup ("<big><b>%s</b></big>" % title)
        d.format_secondary_text (description)
        def response (dialog, response):
            if response == gtk.RESPONSE_YES:
                print >> self.connection.client, "unseek"
            dialog.hide()
        d.connect("response", response)
        d.show()

############################################################################
# Initialize connects for createBoard and createObsBoard                   #
############################################################################

class CreatedBoards (Section):

    def __init__ (self, widgets, connection):
        self.connection = connection
        self.connection.bm.connect ("playBoardCreated", self.playBoardCreated)
        self.connection.bm.connect ("observeBoardCreated", self.observeBoardCreated)

    def playBoardCreated (self, bm, board):

        if board["wms"] == 0 and board["bms"] == 0:
            timemodel = None
        else:
            timemodel = TimeModel (board["wms"]/1000., board["gain"], bsecs=board["bms"]/1000.)
        game = ICGameModel (self.connection, board["gameno"], timemodel, variants[board["variant"]], board["rated"])
        game.connect("game_started", lambda gamemodel: self.connection.bm.onGameModelStarted(board["gameno"]))

        if board["wname"].lower() == self.connection.getUsername().lower():
            player0tup = (LOCAL, Human, (WHITE, "", board["wname"]), _("Human"), board["wrating"])
            player1tup = (REMOTE, ICPlayer,
                    (game, board["bname"], board["gameno"], BLACK), board["bname"], board["brating"])
        else:
            player1tup = (LOCAL, Human, (BLACK, "", board["bname"]), _("Human"), board["brating"])
            # If the remote player is WHITE, we need to init him right now, so
            # we can catch fast made moves
            player0 = ICPlayer(game, board["wname"], board["gameno"], WHITE)
            player0tup = (REMOTE, lambda:player0, (), board["wname"], board["wrating"])

        if not board["fen"]:
            ionest.generalStart(game, player0tup, player1tup)
        else:
            ionest.generalStart(game, player0tup, player1tup,
                                (StringIO(board["fen"]), fen, 0, -1))

    def observeBoardCreated (self, bm, board):

        if board["wms"] == 0 and board["bms"] == 0:
            timemodel = None
        else:
            timemodel = TimeModel (board["wms"]/1000., board["gain"], bsecs=board["bms"]/1000.)
        game = ICGameModel (self.connection, board["gameno"], timemodel, variants[board["variant"]], board["rated"])
        game.connect("game_started", lambda gamemodel: self.connection.bm.onGameModelStarted(board["gameno"]))

        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        player0 = ICPlayer(game, board["wname"], board["gameno"], WHITE)
        player1 = ICPlayer(game, board["bname"], board["gameno"], BLACK)

        player0tup = (REMOTE, lambda:player0, (), board["wname"], board["wrating"])
        player1tup = (REMOTE, lambda:player1, (), board["bname"], board["brating"])

        ionest.generalStart(game, player0tup, player1tup,
                            (StringIO(board["pgn"]), pgn, 0, -1))
