# -*- coding: utf-8 -*-

from Queue import Queue
from Queue import Empty as EmptyError
from cStringIO import StringIO
from time import sleep
from math import e
import webbrowser

import gtk, pango, re
from gtk import gdk
from gtk.gdk import pixbuf_new_from_file

from pychess.System import glock, uistuff
from pychess.System.GtkWorker import EmitPublisher, Publisher
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.widgets import ionest
from pychess.widgets import gamewidget
from pychess.Utils.const import *
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.GameModel import GameModel
from pychess.Players.ServerPlayer import ServerPlayer
from pychess.Players.Human import Human

from GameListManager import GameListManager
from FingerManager import FingerManager
from NewsManager import NewsManager
from BoardManager import BoardManager
from OfferManager import OfferManager

from IcGameModel import IcGameModel
from SpotGraph import SpotGraph
import telnet

firstRun = True
def show():
    global firstRun
    if firstRun:
        firstRun=False
        initialize()
    
    widgets["fics_lounge"].show()

icGames = []

def initialize():
    
    global widgets, icGames
    class Widgets:
        def __init__ (self, glades):
            self.widgets = glades
        def __getitem__(self, key):
            return self.widgets.get_widget(key)
    widgets = Widgets(gtk.glade.XML(addDataPrefix("glade/fics_lounge.glade")))
    
    def on_window_delete (window, event):
        widgets["fics_lounge"].hide()
        return True
    widgets["fics_lounge"].connect("delete-event", on_window_delete)
    
    def on_logoffButton_clicked (button):
        print >> telnet.client, "quit"
        telnet.disconnect()
        widgets["fics_lounge"].hide()
    widgets["logoffButton"].connect("clicked", on_logoffButton_clicked)
    
    global glm, fm, nm
    glm = GameListManager()
    fm = FingerManager()
    nm = NewsManager()
    bm = BoardManager()
    om = OfferManager()
    
    uistuff.makeYellow(widgets["cautionBox"])
    uistuff.makeYellow(widgets["cautionHeader"])
    def on_learn_more_clicked (button, *args):
        retur = widgets["ficsCautionDialog"].run()
        widgets["ficsCautionDialog"].hide()
    widgets["caution_learn_more"].connect("clicked", on_learn_more_clicked)
    
    ############################################################################
    # Initialize User Information Section                                      #
    ############################################################################
    
    widgets["usernameLabel"].set_markup("<b>%s</b>" % telnet.curname)
    
    def on_status_changed (client, signal):
        if signal == IC_CONNECTED:
            fm.finger(telnet.curname)
        else:
            dock = widgets["fingerTableDock"]
            dock.remove(dock.get_children()[0])
    telnet.connectStatus (on_status_changed)
    
    def callback (fm, ratings, email, time):
        
        glock.acquire()
        try:
            dock = widgets["fingerTableDock"]
            
            rows = 1
            if ratings: rows += len(ratings)+1
            if email: rows += 1
            if time: rows += 1
            
            table = gtk.Table(6, rows)
            table.props.column_spacing = 12
            table.props.row_spacing = 4
            
            def label(str, xalign=0):
                label = gtk.Label(str)
                label.props.xalign = xalign
                return label
            
            row = 0
            
            if ratings:
                for i, item in enumerate(("Rating", "Win", "Loss", "Draw", "Total")):
                    table.attach(label(_(item), xalign=1), i+1,i+2,0,1)
                
                row += 1
                
                for typ, numbers in ratings.iteritems():
                    table.attach(label(_(typ)+":"), 0, 1, row, row+1)
                    # Remove RD tag, as we want to be compact
                    numbers = numbers[:1] + numbers[2:]
                    for i, number in enumerate(numbers):
                        table.attach(label(_(number), xalign=1), i+1, i+2, row, row+1)
                    row += 1
                
                table.attach(gtk.HSeparator(), 0, 6, row, row+1, ypadding=2)
                row += 1
            
            if email:
                table.attach(label(_("Email")+":"), 0, 1, row, row+1)
                table.attach(label(email), 1, 6, row, row+1)
                row += 1
            
            if time and telnet.registered:
                table.attach(label(_("Spent")+":"), 0, 1, row, row+1)
                s = ""
                if time[0]:
                    if time[0] == "1":
                        s += "%s day" % time[0]
                    else: s += "%s days" % time[0]
                if time[1]:
                    if s: s += ", "
                    if time[1] == "1":
                        s += "%s hour" % time[1]
                    else: s += "%s hrs" % time[1]
                if time[2]:
                    if s: s += ", "
                    if time[2] == "1":
                        s += "%s min" % time[2]
                    else: s += "%s mins" % time[2]
                if time[3]:
                    if s: s += ", "
                    if time[3] == "1":
                        s += "%s sec" % time[3]
                    else: s += "%s secs" % time[3]
                s += " "+_("online in total")
                table.attach(label(s), 1, 6, row, row+1)
                row += 1
            
            table.attach(label(_("Ping")+":"), 0, 1, row, row+1)
            pingLabel = gtk.Label(_("Connecting")+"...")
            pingLabel.props.xalign = 0
            pinger = Pinger("freechess.org")
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
            
            if not telnet.registered:
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games is be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                vbox.add(label0)
                eventbox = gtk.EventBox()
                label1 = gtk.Label()
                label1.set_markup("<span color='blue'><u>%s</u></span>" % _("Register now"))
                eventbox.add(label1)
                vbox.add(eventbox)
                def released (eventbox, event):
                    webbrowser.open("http://freechess.org/Register/index.html")
                    label1.set_markup("<span color='blue'><u>%s</u></span>" % _("Register now"))
                eventbox.connect("button_release_event", released)
                def pressed (eventbox, event):
                    label1.set_markup("<span color='red'><u>%s</u></span>" % _("Register now"))
                eventbox.connect("button_press_event", pressed)
                eventbox.connect_after("realize",
                    lambda w: w.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2)))
            
            dock.add(table)
            dock.show_all()
        finally:
            glock.release()
        
    fm.connect("fingeringFinished", callback)
    
    ############################################################################
    # Initialize News Section                                                  #
    ############################################################################
    
    def on_status_changed (client, signal):
        if signal == IC_CONNECTED:
            nm.start()
        else:
            for child in widgets["newsVBox"].get_children():
                widgets["newsVBox"].remove(child)
    telnet.connectStatus (on_status_changed)
    
    linkre = re.compile("http://(?:www\.)?\w+\.\w{2,4}[^\s]+")
    emailre = re.compile("[\w\.]+@[\w\.]+\.\w{2,4}")
    def callback (nm, news):
        glock.acquire()
        
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
        textbuffer = textview.get_buffer()
        alignment = gtk.Alignment()
        alignment.set_padding(3, 6, 12, 0)
        alignment.props.xscale = 1
        alignment.add(textview)
        
        tags = []
        
        while True:
            linkmatch = linkre.search(details)
            emailmatch = emailre.search(details)
            if not linkmatch and not emailmatch:
                textbuffer.insert (textbuffer.get_end_iter(), details)
                break
            
            if emailmatch and (not linkmatch or \
                    emailmatch.start() < linkmatch.start()):
                s = emailmatch.start()
                e = emailmatch.end()
                type = "email"
            else:
                s = linkmatch.start()
                e = linkmatch.end()
                if details[e-1] == ".":
                    e -= 1
                type = "link"
            textbuffer.insert (textbuffer.get_end_iter(), details[:s])
            
            tag = textbuffer.create_tag (None, foreground="blue",
                    underline=pango.UNDERLINE_SINGLE)
            tags.append([tag, details[s:e], type, textbuffer.get_end_iter()])
            
            textbuffer.insert_with_tags (
                    textbuffer.get_end_iter(), details[s:e], tag)
            
            tags[-1].append(textbuffer.get_end_iter())
            
            details = details[e:]
        
        def on_press_in_textview (textview, event):
            iter = textview.get_iter_at_location (int(event.x), int(event.y))
            if not iter: return
            for tag, link, type, s, e in tags:
                if iter.has_tag(tag):
                    tag.props.foreground = "red"
                    break
        
        def on_release_in_textview (textview, event):
            iter = textview.get_iter_at_location (int(event.x), int(event.y))
            if not iter: return
            for tag, link, type, s, e in tags:
                if iter and iter.has_tag(tag) and \
                        tag.props.foreground_gdk.red == 65535:
                    if type == "link":
                        webbrowser.open(link)
                    else: webbrowser.open("mailto:"+link)
                tag.props.foreground = "blue"
        
        stcursor = gtk.gdk.Cursor(gtk.gdk.XTERM)
        linkcursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
        def on_motion_in_textview(textview, event):
            textview.window.get_pointer()
            iter = textview.get_iter_at_location (int(event.x), int(event.y))
            if not iter: return
            for tag, link, type, s, e in tags:
                if iter.has_tag(tag):
                    textview.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor (
                            linkcursor)
                    break
            else: textview.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(stcursor)
        textview.connect ("motion-notify-event", on_motion_in_textview)
        textview.connect ("leave_notify_event", on_motion_in_textview)
        textview.connect("button_press_event", on_press_in_textview)
        textview.connect("button_release_event", on_release_in_textview)
        
        expander.add(alignment)
        expander.show_all()
        widgets["newsVBox"].pack_end(expander)
        
        glock.release()
        
    nm.connect("readNews", callback)
    
    ############################################################################
    # Console                                                                  #
    ############################################################################
    
    #def on_showConsoleButton_clicked (button):
    #    widgets["consoleVbox"].show()
    #    widgets["showConsoleButton"].hide()
    #widgets["showConsoleButton"].connect(
    #        "clicked", on_showConsoleButton_clicked)
    
    #def on_consoleCloseButton_clicked (button):
    #    width, height = widgets["fics_lounge"].get_size()
    #    widgets["consoleVbox"].hide()
    #    widgets["showConsoleButton"].show()
    #    widgets["fics_lounge"].resize(1, height)
    #widgets["consoleCloseButton"].connect(
    #        "clicked", on_consoleCloseButton_clicked)
    
    ############################################################################
    # Initialize Lists                                                         #
    ############################################################################
    
    def updateLists (listFuncs):
        for func in listFuncs:
            func()
    listPublisher = Publisher(updateLists, Publisher.SEND_LIST)
    listPublisher.start()
    
    def on_status_changed (client, signal):
        if signal == IC_CONNECTED:
            glm.start ()
        else:
            glm.stop ()
    telnet.connectStatus (on_status_changed)
    
    def addColumns (treeview, *columns, **keyargs):
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
    
    def lowLeftSearchPosFunc (treeview, search_dialog):
        x = tv.allocation.x + tv.get_toplevel().window.get_position()[0]
        y = tv.allocation.y + tv.get_toplevel().window.get_position()[1] + \
            tv.allocation.height
        search_dialog.move(x, y)
        search_dialog.show_all()
    
        ########################################################################
        # Initialize Seek List                                                 #
        ########################################################################
    
    tv = widgets["seektreeview"]
    sstore = gtk.ListStore(str, gtk.gdk.Pixbuf, str, int, str, str, str)
    tv.set_model(gtk.TreeModelSort(sstore))
    try:
        tv.set_search_position_func(lowLeftSearchPosFunc)
    except AttributeError:
        # Unknow signal name is raised by gtk < 2.10
        pass
    addColumns (tv, "GameNo", "", _("Name"), _("Rating"), _("Rated"),
                              _("Type"), _("Clock"), hide=[0], pix=[1])
    tv.set_search_column(2)
    
    seeks = {}
    
    seekPix = pixbuf_new_from_file(addDataPrefix("glade/seek.png"))
    def on_seek_add (manager, seek):
        def call ():
            time = "%s min + %s sec" % (seek["t"], seek["i"])
            rated = seek["r"] == "u" and _("Unrated") or _("Rated")
            ti = sstore.append ([seek["gameno"], seekPix, seek["w"],
                                 int(seek["rt"]), rated, seek["tp"], time])
            seeks [seek["gameno"]] = ti
            count = int(widgets["activeSeeksLabel"].get_text().split()[0])+1
            postfix = count == 1 and _("Active Seek") or _("Active Seeks")
            widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        def call ():
            if not gameno in seeks:
                # We ignore removes we haven't added, as it seams fics sends a
                # lot of removes for games it has never told us about
                return
            ti = seeks [gameno]
            if not sstore.iter_is_valid(ti):
                return
            sstore.remove (ti)
            del seeks[gameno]
            count = int(widgets["activeSeeksLabel"].get_text().split()[0])-1
            postfix = count == 1 and _("Active Seek") or _("Active Seeks")
            widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        #FIXME: Shouldn't remove challenges
        def call ():
            sstore.clear()
            seeks.clear()
        listPublisher.put(call)
    glm.connect("clearSeeks", on_seek_clear)
    
    def on_selection_changed (selection):
        anyThingSelected = selection.get_selected()[1] != None
        widgets["acceptButton"].set_sensitive(anyThingSelected)
    tv.get_selection().connect_after("changed", on_selection_changed)
    
    def on_accept (widget, *args):
        model, iter = widgets["seektreeview"].get_selection().get_selected()
        if iter == None: return
        gameno = model.get_value(iter, 0)
        if gameno.startswith("C"):
            print "Sending", "accept", gameno[1:]
            om.acceptIndex(gameno[1:])
        else:
            print "Sending", "play", gameno
            om.playIndex(gameno)
    widgets["acceptButton"].connect("clicked", on_accept)
    tv.connect("row-activated", on_accept)
    
    def playBoardCreated (bm, board):
        print "playBoardCreated"
        timemodel = TimeModel (int(board["mins"])*60, int(board["incr"]))
        game = IcGameModel (bm, om, board["gameno"], timemodel)
        gmwidg = gamewidget.GameWidget(game)
        
        if board["wname"].lower() == telnet.curname.lower():
            color = WHITE
            white = Human(gmwidg, WHITE, board["wname"])
            black = ServerPlayer (
                bm, om, board["bname"], False, board["gameno"], BLACK)
        else:
            color = BLACK
            black = Human(gmwidg, BLACK, board["bname"])
            white = ServerPlayer (
                bm, om, board["wname"], False, board["gameno"], WHITE)
        
        game.setPlayers((white,black))
        
        gmwidg.setTabText("%s %s %s" % (repr(white), _("vs"), repr(black)))
        gmwidg.connect("closed", ionest.closeGame, game)
        if timemodel:
            gmwidg.widgets["ccalign"].show()
            gmwidg.widgets["cclock"].setModel(timemodel)
        
        glock.acquire()
        try:
            ionest.simpleNewGame (game, gmwidg)
            gamewidget.attachGameWidget (gmwidg)
        finally:
            glock.release()
    
    bm.connect ("playBoardCreated", playBoardCreated)
    
    def on_status_changed (client, signal):
        if signal != IC_CONNECTED:
            sstore.clear()
    telnet.connectStatus (on_status_changed)
    
        ########################################################################
        # Initialize Challenge List                                            #
        ########################################################################
    
    challenges = {}
    
    challenPix = pixbuf_new_from_file(addDataPrefix("glade/challenge.png"))
    def onChallengeAdd (om, index, match):
        def call ():
            time = "%s min + %s sec" % (match["t"], match["i"])
            rated = match["r"] == "u" and _("Unrated") or _("Rated")
            ti = sstore.append (["C"+index, challenPix, match["w"],
                                 int(match["rt"]), rated, match["tp"], time])
            challenges [index] = ti
            count = int(widgets["activeSeeksLabel"].get_text().split()[0])+1
            postfix = count == 1 and _("Active Seek") or _("Active Seeks")
            widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    om.connect("onChallengeAdd", onChallengeAdd)
    
    def onChallengeRemove (om, index):
        def call ():
            if not index in challenges: return
            ti = challenges [index]
            if not sstore.iter_is_valid(ti): return
            sstore.remove (ti)
            del challenges [index]
            count = int(widgets["activeSeeksLabel"].get_text().split()[0])-1
            postfix = count == 1 and _("Active Seek") or _("Active Seeks")
            widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    om.connect("onChallengeRemove", onChallengeRemove)
    
        ########################################################################
        # Initialize Seek Graph                                                #
        ########################################################################
    
    graph = SpotGraph()
    
    for rating in (600, 1200, 1800, 2400):
        graph.addYMark(rating/3000., str(rating))
    
    for mins in (3, 6, 12, 24):
        graph.addXMark(e**(-7./mins/1.4), str(mins)+" min")
    
    widgets["graphDock"].add(graph)
    graph.show()
    
    def on_spot_clicked (graph, name):
        print "sending", "play", name
        print >> telnet.client, "play", name
    graph.connect("spotClicked", on_spot_clicked)
    
    def on_seek_add (manager, seek):
        def call ():
            # The lower the -7 number, the steeper the acceleration.
            # 1.4 is opposite
            x = e**(-7/(float(seek["t"])+float(seek["i"])*2/3)/1.4)
            y = seek["rt"].isdigit() and float(seek["rt"])/3000 or 0
            type = seek["r"] == "u" and 1 or 0
            
            text = "%s (%s)" % (seek["w"], seek["rt"])
            rated = seek["r"] == "u" and _("Unrated") or _("Rated")
            text += "\n%s %s" % (rated, seek["tp"])
            text += "\n%s min + %s sec" % (seek["t"], seek["i"])
            
            graph.addSpot(seek["gameno"], text, x, y, type)
        listPublisher.put(call)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        def call ():
            graph.removeSpot(gameno)
        listPublisher.put(call)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        def call ():
            graph.clearSpots()
        listPublisher.put(call)
    glm.connect("clearSeeks", on_seek_clear)
    
    def on_status_changed (client, signal):
        if signal != IC_CONNECTED:
            graph.clearSpots
    telnet.connectStatus (on_status_changed)
    
        ########################################################################
        # Initialize Players List                                              #
        ########################################################################
    
    icons = gtk.icon_theme_get_default()
    l = gtk.ICON_LOOKUP_USE_BUILTIN
    peoplepix = icons.load_icon("stock_people", 15, l)
    bookpix = icons.load_icon("stock_book_blue", 15, l)
    easypix = icons.load_icon("stock_weather-few-clouds", 15, l)
    advpix = icons.load_icon("stock_weather-cloudy", 15, l)
    exppix = icons.load_icon("stock_weather-storm", 15, l)
    cmppix = icons.load_icon("stock_notebook", 15, l)
    
    tv = widgets["playertreeview"]
    playerSelection = tv.get_selection()
    pstore = gtk.ListStore(gtk.gdk.Pixbuf, str, int)
    tv.set_model(gtk.TreeModelSort(pstore))
    addColumns(tv, "", "Name", "Rating", pix=[0])
    tv.get_column(0).set_sort_column_id(0)
    try:
        tv.set_search_position_func(lowLeftSearchPosFunc)
    except AttributeError:
        # Unknow signal name is raised by gtk < 2.10
        pass
    
    def comparefunction (treemodel, iter0, iter1):
        pix0 = treemodel.get_value(iter0, 0)
        pix1 = treemodel.get_value(iter1, 0)
        if type(pix0) == gtk.gdk.Pixbuf and type(pix1) == gtk.gdk.Pixbuf:
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)
    tv.get_model().set_sort_func(0, comparefunction)
    
    players = {}
    
    def on_player_add (manager, player):
        def call ():
            if player["name"] in players: return
            rating = player["r"].isdigit() and int(player["r"]) or 0
            title = player["title"]
            if title == "C" or title == "TD":
                title = cmppix
            elif title == "U":
                title = peoplepix
            elif title == None:
                if rating < 1300:
                    title = easypix
                elif rating < 1600:
                    title = advpix
                else:
                    title = exppix
            else:
                title = bookpix
            ti = pstore.append ([title, player["name"], rating ])
            players [player["name"]] = ti
            count = int(widgets["playersOnlineLabel"].get_text().split()[0])+1
            postfix = count == 1 and _("Player Ready") or _("Players Ready")
            widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("addPlayer", on_player_add)
    
    def on_player_remove (manager, name):
        def call ():
            if not name in players:
                return
            ti = players [name]
            if not pstore.iter_is_valid(ti):
                return
            pstore.remove (ti)
            del players[name]
            count = int(widgets["playersOnlineLabel"].get_text().split()[0])-1
            postfix = count == 1 and _("Player Ready") or _("Players Ready")
            widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("removePlayer", on_player_remove)
    
    def on_selection_changed (selection):
        anyThingSelected = selection.get_selected()[1] != None
        widgets["challengeButton"].set_sensitive(anyThingSelected)
    tv.get_selection().connect_after("changed", on_selection_changed)
    
    def on_status_changed (client, signal):
        if signal != IC_CONNECTED:
            pstore.clear()
    telnet.connectStatus (on_status_changed)
    
        ########################################################################
        # Initialize Games List                                                #
        ########################################################################
    
    icons = gtk.icon_theme_get_default()
    recpix = icons.load_icon("media-record", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
    clearpix = pixbuf_new_from_file(addDataPrefix("glade/board.png"))
    
    tv = widgets["gametreeview"]
    gstore = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str, str)
    tv.set_model(gtk.TreeModelSort(gstore))
    tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    try:
        tv.set_search_position_func(lowLeftSearchPosFunc)
    except AttributeError:
        # Unknow signal name is raised by gtk < 2.10
        pass

    addColumns(tv, "GameNo", "", _("White Player"), _("Black Player"),
                                 _("Game Type"), hide=[0], pix=[1])
    
    tv.get_column(0).set_sort_column_id(0)
    tv.get_model().set_sort_func(0, comparefunction)
    
    games = {}
    
    def searchCallback (model, column, key, iter):
        if model.get_value(iter, 2).lower().startswith(key) or \
           model.get_value(iter, 3).lower().startswith(key):
            return False
        return True
    tv.set_search_equal_func (searchCallback)
    
    def on_game_add (manager, game):
        def call ():
            ti = gstore.append ([game["gameno"], clearpix, game["wn"],
                                 game["bn"], game["type"]])
            games [game["gameno"]] = ti
            count = int(widgets["gamesRunningLabel"].get_text().split()[0])+1
            postfix = count == 1 and _("Game Running") or _("Games Running")
            widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("addGame", on_game_add)
    
    def on_game_remove (manager, gameno):
        def call ():
            if not gameno in games:
                return
            ti = games [gameno]
            if not gstore.iter_is_valid(ti):
                return
            gstore.remove (ti)
            del games[gameno]
            count = int(widgets["gamesRunningLabel"].get_text().split()[0])-1
            postfix = count == 1 and _("Game Running") or _("Games Running")
            widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
        listPublisher.put(call)
    glm.connect("removeGame", on_game_remove)
    
    def observeBoardCreated (bm, gameno, pgn, secs, incr, wname, bname):
        timemodel = TimeModel (secs, incr)
        game = IcGameModel (bm, om, gameno, timemodel)
        white = ServerPlayer (bm, om, wname, True, gameno, WHITE)
        black = ServerPlayer (bm, om, bname, True, gameno, BLACK)
        game.setPlayers((white,black))
        
        gmwidg = gamewidget.GameWidget(game)
        gmwidg.setTabText("%s %s %s" % (wname, _("vs"), bname))
        gmwidg.connect("closed", ionest.closeGame, game)
        
        if timemodel:
            gmwidg.widgets["ccalign"].show()
            gmwidg.widgets["cclock"].setModel(timemodel)
        
        def onClose (handler, closedGmwidg, game):
            if closedGmwidg == gmwidg:
                bm.unobserve(gameno)
                rowiter = games[gameno]
                tv.get_model().get_model().set_value(rowiter, 1, clearpix)
        ionest.handler.connect("game_closed", onClose)
        
        file = StringIO(pgn)
        ionest.simpleLoadGame (game, gmwidg, file, ionest.enddir["pgn"])
        
        glock.acquire()
        try:
            gamewidget.attachGameWidget(gmwidg)
        finally:
            glock.release()
    
    bm.connect("observeBoardCreated", observeBoardCreated)
    
    def on_observe_clicked (widget, *args):
        model, paths = widgets["gametreeview"].get_selection().get_selected_rows()
        for i, path in enumerate(paths):
            rowiter = model.get_iter(path)
            model.get_model().set_value (
                    model.convert_iter_to_child_iter(None,rowiter), 1, recpix)
            gameno = model.get_value(rowiter, 0)
            bm.observe(gameno)
    widgets["observeButton"].connect ("clicked", on_observe_clicked)
    tv.connect("row-activated", on_observe_clicked)
    
    def on_status_changed (client, signal):
        if signal != IC_CONNECTED:
            gstore.clear()
    telnet.connectStatus (on_status_changed)
    
        ########################################################################
        # Initialize Adjourned List                                            #
        ########################################################################
    
    widgets["notebook"].remove_page(4)
    #########
    # We skip adjourned games until Staunton
    ##########
    #if not telnet.registered:
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
    # Initialize Seeking / Challenging                                         #
    ############################################################################
    
    if not telnet.registered:
        widgets["ratedGameCheck"].hide()
        widgets["chaRatedGameCheck"].hide()
    
    liststore = gtk.ListStore(str, str)
    liststore.append(["0 → 1300", _("Easy")])
    liststore.append(["1300 → 1600", _("Advanced")])
    liststore.append(["1600 → 9999", _("Expert")])
    widgets["strengthCombobox"].set_model(liststore)
    cell = gtk.CellRendererText()
    cell.set_property('xalign',1)
    widgets["strengthCombobox"].pack_start(cell)
    widgets["strengthCombobox"].add_attribute(cell, 'text', 1)
    widgets["strengthCombobox"].set_active(0)
    
    liststore = gtk.ListStore(str)
    liststore.append([_("Don't Care")])
    liststore.append([_("Want White")])
    liststore.append([_("Want Black")])
    widgets["colorCombobox"].set_model(liststore)
    widgets["colorCombobox"].set_active(0)
    widgets["chaColorCombobox"].set_model(liststore)
    widgets["chaColorCombobox"].set_active(0)
    
    liststore = gtk.ListStore(str, str)
    chaliststore = gtk.ListStore(str, str)
    for store in (liststore, chaliststore):
        store.append(["15 min + 10", _("Normal")])
        store.append(["5 min + 2", _("Blitz")])
        store.append(["1 min + 0", _("Lightning")])
        store.append(["", _("New Custom")])
    cell = gtk.CellRendererText()
    cell.set_property('xalign',1)
    widgets["timeCombobox"].set_model(liststore)
    widgets["timeCombobox"].pack_start(cell)
    widgets["timeCombobox"].add_attribute(cell, 'text', 1)
    widgets["timeCombobox"].set_active(0)
    widgets["chaTimeCombobox"].set_model(chaliststore)
    widgets["chaTimeCombobox"].pack_start(cell)
    widgets["chaTimeCombobox"].add_attribute(cell, 'text', 1)
    widgets["chaTimeCombobox"].set_active(0)
    
    customTimeDialog = widgets["customTimeDialog"]
    def timeComboboxChanged (combo, othercombo):
        if combo.get_active() == 3:
            response = customTimeDialog.run()
            customTimeDialog.hide()
            if response != gtk.RESPONSE_OK:
                combo.set_active(combo.old_active)
                return
            if len(combo.get_model()) == 5:
                del combo.get_model()[4]
            minutes = widgets["minSpinbutton"].get_value()
            gain = widgets["gainSpinbutton"].get_value()
            text = "%d min + %d" % (minutes, gain)
            combo.get_model().append([text, _("Custom")])
            combo.set_active(4)
        else: combo.old_active = combo.get_active()
    widgets["timeCombobox"].old_active = 0
    widgets["timeCombobox"].connect("changed", timeComboboxChanged, widgets["chaTimeCombobox"])
    widgets["chaTimeCombobox"].old_active = 0
    widgets["chaTimeCombobox"].connect("changed", timeComboboxChanged, widgets["timeCombobox"])
    
    def seekButtonClicked (button):
        ratingrange = map(int, widgets["strengthCombobox"].get_model()[
                widgets["strengthCombobox"].get_active()][0].split(" → "))
        rated = widgets["ratedGameCheck"].get_active()
        color = widgets["colorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, widgets["timeCombobox"].get_model()[
                widgets["timeCombobox"].get_active()][0].split(" min +"))
        glm.seek(min, incr, rated, ratingrange, color)
    widgets["seekButton"].connect("clicked", seekButtonClicked)
    
    def challengeButtonClicked (button):
        model, iter = playerSelection.get_selected()
        if iter == None: return
        playerName = model.get_value(iter, 1)
        rated = widgets["chaRatedGameCheck"].get_active()
        color = widgets["chaColorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, widgets["chaTimeCombobox"].get_model()[
                widgets["chaTimeCombobox"].get_active()][0].split(" min +"))
        glm.challenge(playerName, min, incr, rated, color)
    widgets["challengeButton"].connect("clicked", challengeButtonClicked)
