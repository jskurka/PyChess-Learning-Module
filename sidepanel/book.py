import gtk, gobject, cairo

__title__ = _("Opening Book")

widgets = gtk.glade.XML("sidepanel/book.glade")
tv = widgets.get_widget("treeview")
sw = widgets.get_widget("scrolledwindow")
sw.unparent()
__widget__ = gtk.Alignment(0,0,1,1)
__widget__.add(sw)

store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
def ready (window):
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn("Move", gtk.CellRendererText(), text=0))
    r = gtk.CellRendererText()
    r.set_property("xalign", 1)
    tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
    tv.append_column(gtk.TreeViewColumn("Win/Draw/Loss", window.BookCellRenderer(), data=2))
    
    global board
    board = window["BoardControl"].view
    board.connect("shown_changed", shown_changed)
    tv.connect("cursor_changed", selection_changed)
    tv.connect("select_cursor_row", selection_changed)
    
int2 = lambda x: x and int(x) or 0
float2 = lambda x: x and float(x) or 0.0

def sortbook (x, y):
    xgames = sum(map(int2,x[2:5]))
    ygames = sum(map(int2,y[2:5]))
    return ygames - xgames

from Utils.book import getOpenings

def shown_changed (board, shown):
    global openings
    openings = getOpenings(board.history, shown)
    openings.sort(sortbook)
    
    board.bluearrow = None
    
    def helper():
        store.clear()
        
        if not openings and __widget__.get_child() == sw:
            __widget__.remove(sw)
            label = gtk.Label(_("In this position,\nthere is no book move."))
            label.set_property("yalign",0.1)
            __widget__.add(label)
            __widget__.show_all()
            return
        if openings and __widget__.get_child() != sw:
            __widget__.remove(__widget__.get_child())
            __widget__.add(sw)
        
        i = 0
        for move, wins, draws, loses in openings:
            wins,draws,loses = map(float2, (wins,draws,loses))
            games = wins+draws+loses
            if not games: continue
            wins,draws,loses = map(lambda x: x/games, (wins,draws,loses))
            store.append ([move, str(int(games)), (wins,draws,loses)])
    gobject.idle_add(helper)

from Utils.Move import movePool

def selection_changed (widget):
    if len(board.history) != board.shown+1:
        # History/moveparsing model, sucks, sucks, sucks
        board.bluearrow = None
        return
    
    iter = tv.get_selection().get_selected()[1]
    if iter == None:
        board.bluearrow = None
        return
    else: sel = tv.get_model().get_path(iter)[0]
    
    move = movePool.pop(board.history, openings[sel][0])
    board.bluearrow = move.cords
    movePool.add(move)
