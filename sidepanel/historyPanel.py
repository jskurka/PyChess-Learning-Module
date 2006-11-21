import gtk, gobject
from gtk import gdk
from pychess.widgets import gamewidget
from pychess.Utils.Move import toSAN
from pychess.Utils.const import prefix

from gtk.gdk import keyval_from_name
leftkeys = map(keyval_from_name,("Left", "KP_Left"))
rightkeys = map(keyval_from_name,("Right", "KP_Right"))

__title__ = _("Move History")
__active__ = True

def fixList (list, xalign=0):
    list.set_model(gtk.ListStore(str))
    renderer = gtk.CellRendererText()
    renderer.set_property("xalign",xalign)
    #import pango
    #renderer.set_property("alignment", "left")
    list.append_column(gtk.TreeViewColumn(None, renderer, text=0))

def idle_add(proc, *args):
    """Makes sure function is only called once"""
    def proc_star():
        proc(*args)
        return False
    gobject.idle_add(proc_star)

class Sidepanel:

    def load (self, window, gmwidg):
        
        widgets = gtk.glade.XML(prefix("sidepanel/history.glade"))
        __widget__ = widgets.get_widget("panel")
        __widget__.unparent()
        
        __active__ = True
        
        self.numbers = widgets.get_widget("treeview1")
        self.left = widgets.get_widget("treeview2")
        self.right = widgets.get_widget("treeview3")

        fixList(self.numbers, 1)
        map(fixList, (self.left, self.right))
        self.numbers.modify_fg(gtk.STATE_INSENSITIVE, gtk.gdk.Color(0,0,0))
        
        widgets.signal_autoconnect ({
            "treeview1_selection_changed": lambda w: self.select_cursor_row(w,1), 
            "treeview2_selection_changed": lambda w: self.select_cursor_row(w,2), 
            "treeview3_selection_changed": lambda w: self.select_cursor_row(w,3),
            "on_treeview2_key_press_event": lambda w,e: self.key_press_event(1,e),
            "on_treeview3_key_press_event": lambda w,e: self.key_press_event(2,e)
        })
        
        self.board = gmwidg.widgets["board"].view
        
        self.board.history.connect("cleared", self.new_history_object)
        self.board.history.connect("changed", self.history_changed)
        self.board.connect("shown_changed", self.shown_changed)
        
        return __widget__
    
    def select_cursor_row (self, tree, col):
        iter = tree.get_selection().get_selected()[1]
        if iter == None: return
        else: sel = tree.get_model().get_path(iter)[0]
        self.board.shown = sel*2+col-1

    def key_press_event (self, col, event):
        if event.keyval in leftkeys and col == 2:
            shown = self.board.shown - 1
            w = left
        elif event.keyval in rightkeys and col == 1:
            shown = self.board.shown + 1
            w = right
        else: return
        row = int((shown-1) / 2)
        def todo():
            w.set_cursor((row,))
            w.grab_focus()
        idle_add(todo)

    def new_history_object (self, history):
        def helper():
            self.left.get_model().clear()
            self.right.get_model().clear()
            self.numbers.get_model().clear()
        gobject.idle_add(helper)

    def history_changed (self, history):
        
        if not history.moves: return
    
        if len(history) % 2 == 0:
            num = str(int(len(history)/2))+"."
            idle_add(self.numbers.get_model().append, [num])
    
        view = len(history) & 1 and self.right or self.left
        notat = toSAN(history[-2], history[-1], history.moves[-1])
    
        def todo():
            view.get_model().append([notat])
            if self.board.shown < len(history):
                return
            shown = len(history)-1
            row = int((shown-1) / 2)
            view.get_selection().select_iter(view.get_model().get_iter(row))
            other = shown & 1 and right or left
            other.get_selection().unselect_all()
    
        idle_add(todo)
        
        if self.board.shown < len(history):
            return
        idle_add(widgets.get_widget("panel").get_vscrollbar().set_value,
                self.numbers.get_allocation().height)

    def shown_changed (self, board, shown):
        if shown <= 0:
            def todo():
                self.left.get_selection().unselect_all()
                self.right.get_selection().unselect_all()
            idle_add(todo)
            return
        
        col = shown & 1 and self.left or self.right
        other = shown & 1 and self.right or self.left
        row = int((shown-1) / 2)
        def todo():
            col.get_selection().select_iter(col.get_model().get_iter(row))
            self.numbers.scroll_to_cell((row,))
            other.get_selection().unselect_all()
        idle_add(todo)
