widgets = None
def set_widgets (w):
	global widgets
	widgets= w

import gtk, os

from System import myconf
from ChessClock import ChessClock
from BoardControl import BoardControl
from ToggleComboBox import ToggleComboBox

icons = gtk.icon_theme_get_default()
light_on = icons.load_icon("stock_3d-light-on", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
light_off = icons.load_icon("stock_3d-light-off", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
gtk_close = icons.load_icon("gtk-close", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
gtk_close20 = icons.load_icon("gtk-close", 20, gtk.ICON_LOOKUP_USE_BUILTIN)

media_previous = icons.load_icon("media-skip-backward", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
media_rewind = icons.load_icon("media-seek-backward", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
media_forward = icons.load_icon("media-seek-forward", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
media_next = icons.load_icon("media-skip-forward", 16, gtk.ICON_LOOKUP_USE_BUILTIN)

def createImage (pixbuf):
	image = gtk.Image()
	image.set_from_pixbuf(pixbuf)
	return image

def createAlignment (top, right, bottom, left):
	align = gtk.Alignment(.5, .5, 1, 1)
	align.set_property("top-padding", top)
	align.set_property("right-padding", right)
	align.set_property("bottom-padding", bottom)
	align.set_property("left-padding", left)
	return align
	
def show_side_panel (page_num, show=True):
	sidepanel = getWidgets(page_num)[2]
	if show:
		sidepanel.show()
		if sidepanel.get_allocation().width > 1:
			panelWidth = sidepanel.get_allocation().width
		else: panelWidth = sidepanel.get_size_request()[0] +10
		widgetsSize = widgets["window1"].get_size()
		widgets["window1"].resize(widgetsSize[0]+panelWidth,widgetsSize[1])
	else:
		panelWidth = sidepanel.get_allocation().width
		sidepanel.hide()
		widgetsSize = widgets["window1"].get_size()
		widgets["window1"].resize(widgetsSize[0]-panelWidth,widgetsSize[1])
	
def addSidepanels (notebook, toggleComboBox, page_num):
	start = 0
	
	path = os.path.join(os.path.split(__file__)[0], "sidepanel") 
	panels = ["sidepanel/"+f for f in os.listdir("sidepanel")]
	panels = [f[:-3] for f in panels if f.endswith(".py")]
	for panel in [__import__(f, locals()) for f in panels]:
		panel.ready(widgets, page_num)
		toggleComboBox.addItem(panel.__title__)
		num = notebook.append_page(panel.__widget__)
		panel.__widget__.show()
		if hasattr(panel, "__active__") and panel.__active__:
			start = num
	
	return start

def addGameTab (title):
	vbox = widgets["mainvbox"]
	if len(vbox.get_children()) == 2:
		vbox.remove(vbox.get_children()[1])
		align = createAlignment (4, 2, 0, 2)
		align.set_property("yscale", 0)
		headbook = gtk.Notebook()
		headbook.set_scrollable(True)
		align.add(headbook)
		
		mainbook = gtk.Notebook()
		mainbook.set_show_tabs(False)
		mainbook.set_show_border(False)
		def callback (widget, page, page_num):
			mainbook.set_current_page(page_num)
		headbook.connect("switch_page", callback)

		vbox.pack_start(align, expand=False)
		vbox.pack_start(mainbook)
	
	headbook = vbox.get_children()[1].child
	
	hbox = gtk.HBox(False, 2)
	hbox.pack_start(createImage(light_off), expand=False)
	close_button = gtk.Button()
	close_button.add(createImage(gtk_close))
	close_button.set_relief(gtk.RELIEF_NONE)
	close_button.set_size_request(21,20)
	def callback (widget):
		print "Closebutton %d activated" % (headbook.get_n_pages()-1)
	close_button.connect("clicked", callback)
	hbox.pack_end(close_button, expand=False)
	hbox.pack_end(gtk.Label(title))
	
	hbox.show_all() # Gtk doesn't show tablabels when the rest is show_all'ed
	headbook.append_page(gtk.HSeparator(), hbox)
	
	mainbook = vbox.get_children()[2]
	
	page_num = headbook.get_n_pages()-1
	
	mvbox = gtk.VBox()
	
	align = createAlignment (3, 2, 4, 2)
	
	hbox = gtk.HBox()
	hbox.set_spacing(4)	
	
	lvbox = gtk.VBox()
	lvbox.set_spacing(4)
	
	ccalign = createAlignment(0,0,0,0)
	cclock = ChessClock()
	ccalign.add(cclock)
	ccalign.set_size_request(-1, 32)
	board = BoardControl()
	
	lvbox.pack_start(ccalign, expand=False)
	lvbox.pack_start(board)
	rvbox = gtk.VBox()
	rvbox.set_spacing(4)
	
	top_align = createAlignment(0,0,0,0)
	top_align.set_size_request(-1, 32)
	
	side_top_hbox = gtk.HBox()
	
	toggle_combox = ToggleComboBox()
	side_closebut = gtk.Button()
	side_closebut.add(createImage(gtk_close20))
	side_closebut.connect("clicked", lambda w: show_side_panel(page_num, False))
	side_closebut.set_relief(gtk.RELIEF_NONE)
	
	side_top_hbox.pack_start(toggle_combox)
	side_top_hbox.pack_start(side_closebut, expand=False)
	side_book = gtk.Notebook()
	side_book.set_show_border(False)
	side_book.set_show_tabs(False)
	
	top_align.add(side_top_hbox)
	
	rvbox.pack_start(top_align, expand=False)
	rvbox.pack_start(side_book)
	
	hbox.pack_start(lvbox)
	hbox.pack_start(rvbox, expand=False)
	
	align.add(hbox)
	
	stat_hbox = gtk.HBox()
	
	page_vbox = gtk.VBox()
	page_vbox.set_spacing(1)
	
	sep = gtk.HSeparator()
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
	
	def setshown (shown): board.view.shown = shown
	startbut.connect("clicked", lambda w: setshown(0))
	backbut.connect("clicked", lambda w: setshown(board.view.shown-1))
	forwbut.connect("clicked", lambda w: setshown(board.view.shown+1))
	endbut.connect("clicked", lambda w: setshown(len(board.view.history)-1))
	
	page_hbox.pack_start(startbut)
	page_hbox.pack_start(backbut)
	page_hbox.pack_start(forwbut)
	page_hbox.pack_start(endbut)
	
	page_vbox.pack_start(sep)
	page_vbox.pack_start(page_hbox)
	
	statusbar = gtk.Statusbar()
	
	stat_hbox.pack_start(page_vbox, expand=False)
	stat_hbox.pack_start(statusbar)
	
	mvbox.pack_start(align)
	mvbox.pack_start(stat_hbox, expand=False)
	
	mainbook.append_page(mvbox, None)
	
	start = addSidepanels(side_book, toggle_combox, page_num)
	toggle_combox.connect("changed", lambda w,i: side_book.set_current_page(i))
	side_book.set_current_page(start)
	toggle_combox.active = start
	
	vbox.show_all()
	
def setTabReady (page_num, ready):
	headbook = widgets["mainvbox"].get_children()[1].child
	if headbook.get_n_pages() <= page_num:
		raise IndexError, "Tab index out of range %d <= %d" % \
			(headbook.get_n_pages(), page_num)
	
	page = headbook.get_nth_page(page_num)
	hbox = headbook.get_tab_label(page)
	hbox.remove(hbox.get_children()[0])
	if ready:
		hbox.pack_start(createImage(light_on), expand=False)
	else: hbox.pack_start(createImage(light_off), expand=False)
	hbox.show_all()
	
def getWidgets (page_num):
	headbook = widgets["mainvbox"].get_children()[1].child
	if headbook.get_n_pages() <= page_num:
		raise IndexError, "Tab index out of range %d <= %d" % \
			(headbook.get_n_pages(), page_num)
	
	mvbox = widgets["mainvbox"].get_children()[2].get_nth_page(page_num)
	
	board = mvbox.get_children()[0].child.get_children()[0].get_children()[1]
	cclock = mvbox.get_children()[0].child.get_children()[0].get_children()[0].child
	side = mvbox.get_children()[0].child.get_children()[1]
	
	return (board, cclock, side)
