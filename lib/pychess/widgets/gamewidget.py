
""" This module handles the tabbed layout in PyChess """

import imp, os, atexit

import gtk, gobject, gdl
from gtk import ICON_LOOKUP_USE_BUILTIN

from pychess.System import glock, conf, prefix
from ChessClock import ChessClock
from BoardControl import BoardControl
from pydock.PyDockTop import PyDockTop
from pydock.__init__ import CENTER, WEST
from pychess.System.prefix import addHomePrefix

################################################################################
# Initialize modul constants, and a few worker functions                       #
################################################################################

def createAlignment (top, right, bottom, left):
    align = gtk.Alignment(.5, .5, 1, 1)
    align.set_property("top-padding", top)
    align.set_property("right-padding", right)
    align.set_property("bottom-padding", bottom)
    align.set_property("left-padding", left)
    return align

def cleanNotebook ():
    notebook = gtk.Notebook()
    notebook.set_show_tabs(False)
    notebook.set_show_border(False)
    return notebook

icons = gtk.icon_theme_get_default()
def lookup16 (name, alternative=None):
    try:
        return icons.load_icon(name, 16, ICON_LOOKUP_USE_BUILTIN)
    except:
        return icons.load_icon(alternative, 16, ICON_LOOKUP_USE_BUILTIN)

def createImage (pixbuf):
    image = gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image

light_on = lookup16("stock_3d-light-on", "weather-clear")
light_off = lookup16("stock_3d-light-off", "weather-clear-night")
gtk_close = lookup16("gtk-close")

media_previous = lookup16("stock_media-prev")
media_rewind = lookup16("stock_media-rew")
media_forward = lookup16("stock_media-fwd")
media_next = lookup16("stock_media-next")

GAME_MENU_ITEMS = ("save_game1", "save_game_as1", "properties1", "close1")
ACTION_MENU_ITEMS = ("draw", "pause1", "resume1", "undo1", 
                     "call_flag", "resign", "ask_to_move")
VIEW_MENU_ITEMS = ("rotate_board1", "rearrange_panels", "hint_mode", "spy_mode")
MENU_ITEMS = GAME_MENU_ITEMS + ACTION_MENU_ITEMS + VIEW_MENU_ITEMS

path = prefix.addDataPrefix("sidepanel")
postfix = "Panel.py"
files = [f[:-3] for f in os.listdir(path) if f.endswith(postfix)]
sidePanels = [imp.load_module(f, *imp.find_module(f, [path])) for f in files]


################################################################################
# Initialize module variables                                                  #
################################################################################

widgets = None
def setWidgets (w):
    global widgets
    widgets = w

key2gmwidg = {}
notebooks = {"board": cleanNotebook(), "statusbar": cleanNotebook()}
for panel in sidePanels:
    notebooks[panel.__title__] = cleanNotebook()

################################################################################
# The holder class for tab releated widgets                                    #
################################################################################

class GameWidget (gobject.GObject):
    
    __gsignals__ = {
        'close_clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
        'infront': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
        'closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
    }
    
    def __init__ (self, gamemodel):
        gobject.GObject.__init__(self)
        self.gamemodel = gamemodel
        
        tabcontent = self.initTabcontents()
        boardvbox, board = self.initBoardAndClock(gamemodel)
        statusbar, stat_hbox = self.initStatusbar(board)
        
        self.tabcontent = tabcontent
        self.board = board
        self.statusbar = statusbar
        
        self.notebookKey = gtk.Label()
        self.notebookKey.set_size_request(0,0)
        self.boardvbox = boardvbox
        self.stat_hbox = stat_hbox
        
        # Some stuff in the sidepanels .load functions might change UI, so we
        # need glock
        # TODO: Really?
        glock.acquire()
        try:
            self.panels = [panel.Sidepanel().load(self) for panel in sidePanels]
        finally:
            glock.release()
    
    def initTabcontents(self):
        tabcontent = createAlignment(gtk.Notebook().props.tab_vborder,0,0,0)
        hbox = gtk.HBox()
        hbox.set_spacing(4)
        hbox.pack_start(createImage(light_off), expand=False)
        close_button = gtk.Button()
        close_button.set_property("can-focus", False)
        close_button.add(createImage(gtk_close))
        close_button.set_relief(gtk.RELIEF_NONE)
        close_button.set_size_request(20, 18)
        close_button.connect("clicked", lambda w: self.emit("close_clicked"))
        hbox.pack_end(close_button, expand=False)
        label = gtk.Label("")
        label.set_alignment(0,.7)
        hbox.pack_end(label)
        tabcontent.add(hbox)
        tabcontent.show_all() # Gtk doesn't show tab labels when the rest is
        return tabcontent
    
    def initBoardAndClock(self, gamemodel):
        boardvbox = gtk.VBox()
        boardvbox.set_spacing(2)
        if gamemodel.timemodel:
            ccalign = createAlignment(0, 0, 0, 0)
            cclock = ChessClock()
            cclock.setModel(gamemodel.timemodel)
            ccalign.add(cclock)
            ccalign.set_size_request(-1, 32)
            boardvbox.pack_start(ccalign, expand=False)
        
        actionMenuDic = {}
        for item in ACTION_MENU_ITEMS:
            actionMenuDic[item] = widgets[item]
        
        board = BoardControl(gamemodel, actionMenuDic)
        boardvbox.pack_start(board)
        return boardvbox, board
    
    def initStatusbar(self, board):
        stat_hbox = gtk.HBox()
        page_vbox = gtk.VBox()
        page_vbox.set_spacing(1)
        sep = gtk.HSeparator()
        sep.set_size_request(-1, 2)
        page_hbox = gtk.HBox()
        startbut = gtk.Button()
        startbut.add(createImage(media_previous))
        startbut.set_relief(gtk.RELIEF_NONE)
        backbut = gtk.Button()
        backbut.add(createImage(media_rewind))
        backbut.set_relief(gtk.RELIEF_NONE)
        forwbut = gtk.Button()
        forwbut.add(createImage(media_forward))
        forwbut.set_relief(gtk.RELIEF_NONE)
        endbut = gtk.Button()
        endbut.add(createImage(media_next))
        endbut.set_relief(gtk.RELIEF_NONE)
        startbut.connect("clicked", lambda w: board.view.showFirst())
        backbut.connect("clicked", lambda w: board.view.showPrevious())
        forwbut.connect("clicked", lambda w: board.view.showNext())
        endbut.connect("clicked", lambda w: board.view.showLast())
        page_hbox.pack_start(startbut)
        page_hbox.pack_start(backbut)
        page_hbox.pack_start(forwbut)
        page_hbox.pack_start(endbut)
        page_vbox.pack_start(sep)
        page_vbox.pack_start(page_hbox)
        statusbar = gtk.Statusbar()
        stat_hbox.pack_start(page_vbox, expand=False)
        stat_hbox.pack_start(statusbar)
        return statusbar, stat_hbox
    
    def setLocked (self, locked):
        """ Makes the board insensitive and turns of the tab ready indicator """
        self.board.setLocked(locked)
        self.tabcontent.child.remove(self.tabcontent.child.get_children()[0])
        if not locked:
            self.tabcontent.child.pack_start(createImage(light_on), expand=False)
        else: self.tabcontent.child.pack_start(createImage(light_off), expand=False)
        self.tabcontent.show_all()
    
    def setTabText (self, text):
        self.tabcontent.child.get_children()[1].set_text(text)
    
    def getTabText (self):
        return self.tabcontent[1].get_text()
    
    def status (self, message):
        glock.acquire()
        try:
            self.statusbar.pop(0)
            if message:
                self.statusbar.push(0, message)
        finally:
            glock.release()
    
    def bringToFront (self):
        getheadbook().set_current_page(self.getPageNumber())
    
    def getPageNumber (self):
        return getheadbook().page_num(self.notebookKey)
    
    def connectToTabs (self, notebook):
        mainbook = gtk.Notebook()
        mainbook.set_show_tabs(False)
        mainbook.set_show_border(False)
        def callback (widget, page, page_num):
            mainbook.set_current_page(page_num)
        headbook.connect("switch_page", callback)
        try:
            def page_reordered (widget, child, new_page_num):
                mainbook.reorder_child (
                        head2mainDic[child].widgets["mvbox"], new_page_num)
            headbook.connect("page-reordered", page_reordered)
        except TypeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        mainbook.show_all()


################################################################################
# Main handling of gamewidgets                                                 #
################################################################################

def delGameWidget (gmwidg):
    """ Remove the widget from the GUI after the game has been terminated """
    gmwidg.emit("closed")
    
    del key2gmwidg[gmwidg.notebookKey]
    pageNum = gmwidg.getPageNumber()
    headbook = getheadbook()
    
    headbook.remove_page(pageNum)
    for notebook in notebooks.values():
        notebook.remove_page(pageNum)
    
    if headbook.get_n_pages() == 1 and conf.get("hideTabs", False):
        show_tabs(False)
    
    if headbook.get_n_pages() == 0:
        mainvbox = widgets["mainvbox"]
        mainvbox.remove(mainvbox.get_children()[2])
        mainvbox.remove(mainvbox.get_children()[1])
        mainvbox.pack_end(background)
        background.show()

def _ensureReadForGameWidgets ():
    mainvbox = widgets["mainvbox"]
    if len(mainvbox.get_children()) == 3:
        return
    
    global background
    background = widgets["mainvbox"].get_children()[1]
    mainvbox.remove(background)
    
    # Initing headbook
    
    align = createAlignment (2, 2, 0, 2)
    align.set_property("yscale", 0)
    headbook = gtk.Notebook()
    headbook.set_scrollable(True)
    headbook.props.tab_vborder = 0
    align.add(headbook)
    mainvbox.pack_start(align, expand=False)
    if not conf.get("hideTabs", False):
        align.show_all()
    
    # Initing center
    
    centerVBox = gtk.VBox()
    centerVBox.set_spacing(3)
    centerVBox.set_border_width(3)
    dock = PyDockTop("main")
    centerVBox.pack_start(dock)
    dock.show()
    
    dockLocation = addHomePrefix("pydock.xml")
    docks = {"board": ("Board", notebooks["board"])}
    for id, panel in zip(files, sidePanels):
        hbox = gtk.HBox()
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(panel.__icon__, 16, 16)
        icon = gtk.image_new_from_pixbuf(pixbuf)
        label = gtk.Label(panel.__title__)
        label.set_size_request(0, 0)
        label.set_alignment(0, 1)
        hbox.pack_start(icon, expand=False, fill=False)
        hbox.pack_start(label, expand=True, fill=True)
        hbox.set_spacing(2)
        hbox.show_all()
        
        tip = gtk.Tooltip()
        def cb (widget, x, y, keyboard_mode, tooltip, title, desc, pixbuf):
            tooltip.set_markup("<b>%s</b>\n%s" % (title,desc))
            tooltip.set_icon(pixbuf)
            return True
        hbox.props.has_tooltip = True
        hbox.connect("query-tooltip", cb, panel.__title__, panel.__desc__,
                     gtk.gdk.pixbuf_new_from_file_at_size(panel.__icon__, 48, 48))
        
        docks[str(id)] = (hbox, notebooks[panel.__title__])
    
    if False and os.path.isfile(dockLocation):
        dock.loadFromXML(dockLocation, docks)
    else:
        for id in files:
            title, panel = docks[str(id)]
            leaf = dock.dock(panel, CENTER, title, str(id))
        leaf = dock.dock(docks["board"][1], WEST, gtk.Label(docks["board"][0]), "board")
        leaf.get_parent().set_position(500)
        docks["board"][1].show_all()
        leaf.setDockable(False)
    
    #def callback():
    #    dock.saveToXML(dockLocation)
    #atexit.register(callback)
    
    centerVBox.pack_start(notebooks["statusbar"], expand=False)
    mainvbox.pack_start(centerVBox)
    centerVBox.show_all()
    mainvbox.show()
    
    # Connecting headbook to other notebooks
    
    def callback (notebook, gpointer, page_num):
        for notebook in notebooks.values():
            notebook.set_current_page(page_num)
    headbook.connect("switch-page", callback)
    
    if hasattr(headbook, "set_tab_reorderable"):
        def page_reordered (widget, child, new_num, headbook):
            old_num = notebooks["board"].page_num(key2gmwidg[child].board)
            for notebook in notebooks.values():
                notebook.reorder_child(notebook.get_nth_page(old_num), new_num)
        headbook.connect("page-reordered", page_reordered, headbook)

def attachGameWidget (gmwidg):
    _ensureReadForGameWidgets()
    headbook = getheadbook()
    
    key2gmwidg[gmwidg.notebookKey] = gmwidg
    
    headbook.append_page(gmwidg.notebookKey, gmwidg.tabcontent)
    headbook.set_tab_label_packing(gmwidg.notebookKey, True, True, gtk.PACK_START)
    if hasattr(headbook, "set_tab_reorderable"):
        headbook.set_tab_reorderable (gmwidg.notebookKey, True)
    
    def callback (notebook, gpointer, page_num, gmwidg):
        if notebook.get_nth_page(page_num) == gmwidg.notebookKey:
            gmwidg.emit("infront")
    headbook.connect("switch-page", callback, gmwidg)
    
    notebooks["board"].append_page(gmwidg.boardvbox)
    gmwidg.boardvbox.show_all()
    for panel, instance in zip(sidePanels, gmwidg.panels):
        notebooks[panel.__title__].append_page(instance)
        instance.show_all()
    notebooks["statusbar"].append_page(gmwidg.stat_hbox)
    
    # We should always show tabs if more than one exists
    if headbook.get_n_pages() == 2:
        show_tabs(True)
    
    headbook.set_current_page(-1)

def cur_gmwidg ():
    headbook = getheadbook()
    notebookKey = headbook.get_nth_page(headbook.get_current_page())
    return key2gmwidg[notebookKey]

def getheadbook ():
    if len(widgets["mainvbox"].get_children()) == 2:
        # If the headbook hasn't been added yet
        return None
    return widgets["mainvbox"].get_children()[1].child


def show_tabs (show):
    if show:
        widgets["mainvbox"].get_children()[1].show_all()
    else: widgets["mainvbox"].get_children()[1].hide()

def tabsCallback (none):
    head = getheadbook()
    if not head: return
    if head.get_n_pages() == 1:
        if conf.get("hideTabs", False):
            show_tabs(False)
        else:
            show_tabs(True)
conf.notify_add("hideTabs", tabsCallback)

def showGrips (doShow):
    dock = widgets["mainvbox"].get_children()[2].get_children()[0]
    for dockitem in dock.get_children():
        if doShow:
            dockitem.show_grip()
        else:
            dockitem.hide_grip()
