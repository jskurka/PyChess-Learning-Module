import sys

import gtk
import gobject

from pychess.System.prefix import addDataPrefix
from pychess.widgets.BorderBox import BorderBox 

from __init__ import CENTER
from __init__ import DockComposite, DockLeaf
from PyDockComposite import PyDockComposite
from StarArrowButton import StarArrowButton
from HighlightArea import HighlightArea

class PyDockLeaf (DockLeaf):
    def __init__ (self, widget, title, id):
        DockLeaf.__init__(self)
        self.set_no_show_all(True)
        
        self.book = gtk.Notebook()
        self.book.connect("drag-begin", self.__onDragBegin)
        self.book.connect("drag-end", self.__onDragEnd)
        self.book.connect_after("switch-page", self.__onPageSwitched)
        self.put(self.book, 0, 0)
        self.connect("size-allocate", lambda self, alloc: \
                     self.book.set_size_request(alloc.width, alloc.height))
        self.book.show()
        self.book.props.tab_vborder = 0
        self.book.props.tab_hborder = 1
        
        self.highlightArea = HighlightArea()
        self.put(self.highlightArea, 0, 0)
        
        self.starButton = StarArrowButton(addDataPrefix("glade/dock_top.svg"),
                                          addDataPrefix("glade/dock_right.svg"),
                                          addDataPrefix("glade/dock_bottom.svg"),
                                          addDataPrefix("glade/dock_left.svg"),
                                          addDataPrefix("glade/dock_center.svg"),
                                          addDataPrefix("glade/dock_star.svg"))
        self.put(self.starButton, 0, 0)
        self.starButton.connect("dropped", self.__onDrop)
        self.starButton.connect("hovered", self.__onHover)
        self.starButton.connect("left", self.__onLeave)
        
        self.dockable = True
        self.panels = []
        assert isinstance(widget, gtk.Notebook)
        self.__add(widget, title, id)
    
    def __add (self, widget, title, id):
        #widget = BorderBox(widget, top=True)
        self.panels.append((widget, title, id))
        self.book.append_page(widget, title)
        self.book.set_tab_label_packing(widget, True, True, gtk.PACK_START)
        self.book.set_tab_detachable(widget, True)
        self.book.set_tab_reorderable(widget, True)
        widget.show_all()
    
    def dock (self, widget, position, title, id):
        if position == CENTER:
            self.__add(widget, title, id)
            return self
        else:
            parent = self.get_parent()
            while not isinstance(parent, DockComposite):
                parent = parent.get_parent()
            
            leaf = PyDockLeaf(widget, title, id)
            new = PyDockComposite(position)
            parent.changeComponent(self, new)
            new.initChildren(self, leaf)
            new.show_all()
            return leaf
    
    def undock (self, widget):
        for i, (widget_, title, id) in enumerate(self.panels):
            if widget_ == widget:
                break
        else:
            raise KeyError, "No %s in %s" % (widget, self)
        del self.panels[i]
        
        self.book.remove_page(self.book.page_num(widget))
        if self.book.get_n_pages() == 0:
            def cb ():
                parent = self.get_parent()
                while not isinstance(parent, DockComposite):
                    parent = parent.get_parent()
                parent.removeComponent(self)
            # We need to idle_add this, as the widget won't emit drag-ended, if
            # it is removed to early
            gobject.idle_add(cb)
        
        return title, id
    
    def getPanels(self):
        return self.panels
    
    def getCurrentPanel (self):
        for i, (widget, title, id) in enumerate(self.panels):
            if i == self.book.get_current_page():
                return id
    
    def setCurrentPanel (self, id):
        for i, (widget, title, id_) in enumerate(self.panels):
            if id == id_:
                self.book.set_current_page(i)
                break
    
    def isDockable (self):
        return self.dockable
    
    def setDockable (self, dockable):
        self.book.set_show_tabs(dockable)
        #self.book.set_show_border(dockable)
        self.dockable = dockable
    
    
    def showArrows (self):
        if self.dockable:
            self.starButton.show()
    
    def hideArrows (self):
        self.starButton.hide()
        self.highlightArea.hide()
    
    
    def __onDragBegin (self, widget, context):
        for instance in self.getInstances():
            instance.showArrows()
    
    def __onDragEnd (self, widget, context):
        for instance in self.getInstances():
            instance.hideArrows()
    
    def __onDrop (self, starButton, position, sender):
        self.highlightArea.hide()
        if self.dockable:
            child = sender.get_nth_page(sender.get_current_page())
            title, id = sender.get_parent().undock(child)
            self.dock(child, position, title, id)
    
    def __onHover (self, starButton, position, widget):
        if self.dockable:
            starButton.window.raise_()
            self.highlightArea.showAt(position)
    
    def __onLeave (self, starButton):
        self.highlightArea.hide()
    
    
    def __onPageSwitched (self, book, page, page_num):
        # When a tab is dragged over another tab, the page is temporally
        # switched, and the notebook child is hovered. Thus we need to reraise
        # our star
        if self.starButton.window:
            self.starButton.window.raise_()
