# -*- coding: UTF-8 -*-

import os.path

import gtk, pango, gobject

from pychess.System import glock, uistuff
from pychess.System.Log import log
from pychess.System.Log import DEBUG, LOG, WARNING, ERROR
from pychess.System.prefix import addDataPrefix

class InformationWindow:
    
    @classmethod
    def _init (cls):
        cls.tagToIter = {}
        cls.tagToPage = {}
        cls.pathToPage = {}
        
        cls.window = gtk.Window()
        cls.window.set_title("PyChess Information Window")
        cls.window.set_border_width(12)
        mainHBox = gtk.HBox()
        mainHBox.set_spacing(6)
        cls.window.add(mainHBox)
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        mainHBox.pack_start(sw, expand=False)
        cls.treeview = gtk.TreeView(gtk.TreeStore(str))
        cls.treeview.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=0))
        cls.treeview.set_headers_visible(False)
        sw.add(cls.treeview)
        cls.pages = gtk.Notebook()
        cls.pages.set_show_tabs(False)
        cls.pages.set_show_border(False)
        mainHBox.pack_start(cls.pages)
        
        def selectionChanged (selection):
            treestore, iter = selection.get_selected()
            child = cls.pathToPage[treestore.get_path(iter)]["child"]
            cls.pages.set_current_page(cls.pages.page_num(child))
        cls.treeview.get_selection().connect("changed", selectionChanged)
    
    @classmethod
    def show (cls):
        cls.window.show_all()
    
    @classmethod
    def hide (cls):
        cls.window.hide()
    
    @classmethod
    def newMessage (cls, tag, message, importance):
        textview = cls._getPageFromTag(tag)["textview"]
        textview.get_buffer().insert_with_tags_by_name(
            textview.get_buffer().get_end_iter(), message, str(importance))
    
    @classmethod
    def _createPage (cls, parrentIter, tag):
        name = tag[-1]
        iter = cls.treeview.get_model().append(parrentIter, (name,))
        cls.tagToIter[tag] = iter
        
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_NONE)
        cls.pages.append_page(frame)
        label = gtk.Label()
        label.set_markup("<b>Communication</b>")
        frame.set_label_widget(label)
        alignment = gtk.Alignment(1,1,1,1)
        alignment.set_padding(6, 0, 12, 0)
        frame.add(alignment)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        alignment.add(sw)
        textview = gtk.TextView()
        tb = textview.get_buffer()
        tb.create_tag(str(DEBUG), family='Monospace')
        tb.create_tag(str(LOG), family='Monospace', weight=pango.WEIGHT_BOLD)
        tb.create_tag(str(WARNING), family='Monospace', foreground="red")
        tb.create_tag(str(ERROR), family='Monospace', weight=pango.WEIGHT_BOLD, foreground="red")
        sw.add(textview)
        
        frame.show_all()
        page = {"child": frame, "textview":textview}
        cls.tagToPage[tag] = page
        cls.pathToPage[cls.treeview.get_model().get_path(iter)] = page
    
    @classmethod
    def _getPageFromTag (cls, tag):
        if type(tag) == list:
            tag = tuple(tag)
        elif type(tag) != tuple:
            tag = (tag,)
        
        if tag in cls.tagToPage:
            return cls.tagToPage[tag]
        
        for i in xrange(len(tag)-1):
            subtag = tag[:-i-1]
            if subtag in cls.tagToIter:
                newtag = subtag+(tag[len(subtag)],)
                iter = cls.tagToIter[subtag]
                cls._createPage(iter, newtag)
                return cls._getPageFromTag(tag)
        
        cls._createPage(None, tag[:1])
        return cls._getPageFromTag(tag)

################################################################################
# Add early messages and connect for new                                       #
################################################################################

InformationWindow._init()

def addMessages (messages):
    for task, message, type in messages:
        InformationWindow.newMessage (task, message, type)

glock.acquire()
try:
    addMessages(log.messages)
    log.messages = None
finally:
    glock.release()

log.connect ("logged", lambda log, messages: addMessages(messages))

################################################################################
# External functions                                                           #
################################################################################

destroy_funcs = []
def add_destroy_notify (func):
    destroy_funcs.append(func)
def _destroy_notify (widget, *args):
    [func() for func in destroy_funcs]
    return True
InformationWindow.window.connect("delete-event", _destroy_notify)

def show ():
    InformationWindow.show()
    
def hide ():
    InformationWindow.hide()

if __name__ == "__main__":
    show()
    InformationWindow.window.connect("delete-event", gtk.main_quit)
    gtk.main()
