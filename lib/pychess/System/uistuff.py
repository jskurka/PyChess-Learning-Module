
import re, webbrowser

import gtk, pango

from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.widgets.ToggleComboBox import ToggleComboBox

def createCombo (combo, data):
    ls = gtk.ListStore(gtk.gdk.Pixbuf, str)
    for icon, label in data:
        ls.append([icon, label])
    combo.clear()
    
    combo.set_model(ls)
    crp = gtk.CellRendererPixbuf()
    crp.set_property('xalign',0)
    crp.set_property('xpad', 2)
    combo.pack_start(crp, False)
    combo.add_attribute(crp, 'pixbuf', 0)
    
    crt = gtk.CellRendererText()
    crt.set_property('xalign',0)
    crt.set_property('xpad', 4)
    combo.pack_start(crt, True)
    combo.add_attribute(crt, 'text', 1)
    crt.set_property('ellipsize', pango.ELLIPSIZE_MIDDLE)



methodDict = {
    gtk.Entry: ("get_text", "set_text", "changed"),
    gtk.Expander: ("get_expanded", "set_expanded", "notify::expanded"),
    gtk.CheckButton: ("get_active", "set_active", "toggled"),
    gtk.RadioButton: ("get_active", "set_active", "toggled"),
    gtk.ComboBox: ("get_active", "set_active", "changed"),
    ToggleComboBox: ("_get_active", "_set_active", "changed")
}

def keep (widget, key, get_value_=None, set_value_=None, first_value=None):
    if widget == None:
        raise AttributeError, "key '%s' isn't in widgets" % key
    
    if get_value_:
        get_value = lambda: get_value_(widget)
    else:
        get_value = getattr(widget, methodDict[type(widget)][0])
    
    if set_value_:
        set_value = lambda v: set_value_(widget, v)
    else:
        set_value = getattr(widget, methodDict[type(widget)][1])
    
    if first_value != None:
        conf.set(key, first_value)
    if conf.hasKey(key):
        set_value(conf.getStrict(key))
    
    signal = methodDict[type(widget)][2]
    widget.connect(signal, lambda *args: conf.set(key, get_value()))
    conf.notify_add(key, lambda *args: set_value(conf.getStrict(key)))

tooltip = gtk.Tooltips()
tooltip.force_window()
if hasattr(tooltip, 'tip_window') and tooltip.tip_window != None:
    tooltip.tip_window.ensure_style()
    tooltipStyle = tooltip.tip_window.get_style()
else:
    tooltipStyle = None



def makeYellow (box):
    if tooltipStyle:
        box.set_style(tooltipStyle)
    def on_box_expose_event (box, event):
        allocation = box.allocation
        box.style.paint_flat_box (box.window,
            gtk.STATE_NORMAL, gtk.SHADOW_NONE, None, box, "tooltip",
            allocation.x, allocation.y, allocation.width, allocation.height)
        if not hasattr(box, "hasHadFirstDraw") or not box.hasHadFirstDraw:
            box.queue_draw()
            box.hasHadFirstDraw = True
    box.connect("expose-event", on_box_expose_event)



linkre = re.compile("http://(?:www\.)?\w+\.\w{2,4}[^\s]+")
emailre = re.compile("[\w\.]+@[\w\.]+\.\w{2,4}")
def initTexviewLinks (textview, text):
    tags = []
    textbuffer = textview.get_buffer()
    
    while True:
        linkmatch = linkre.search(text)
        emailmatch = emailre.search(text)
        if not linkmatch and not emailmatch:
            textbuffer.insert (textbuffer.get_end_iter(), text)
            break
        
        if emailmatch and (not linkmatch or \
                emailmatch.start() < linkmatch.start()):
            s = emailmatch.start()
            e = emailmatch.end()
            type = "email"
        else:
            s = linkmatch.start()
            e = linkmatch.end()
            if text[e-1] == ".":
                e -= 1
            type = "link"
        textbuffer.insert (textbuffer.get_end_iter(), text[:s])
        
        tag = textbuffer.create_tag (None, foreground="blue",
                underline=pango.UNDERLINE_SINGLE)
        tags.append([tag, text[s:e], type, textbuffer.get_end_iter()])
        
        textbuffer.insert_with_tags (
                textbuffer.get_end_iter(), text[s:e], tag)
        
        tags[-1].append(textbuffer.get_end_iter())
        
        text = text[e:]
    
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



def initLabelLinks (text, url):
    label = gtk.Label()
    
    eventbox = gtk.EventBox()
    label.set_markup("<span color='blue'><u>%s</u></span>" % text)
    eventbox.add(label)
    
    def released (eventbox, event):
        webbrowser.open(url)
        label.set_markup("<span color='blue'><u>%s</u></span>" % text)
    eventbox.connect("button_release_event", released)
    
    def pressed (eventbox, event):
        label.set_markup("<span color='red'><u>%s</u></span>" % text)
    eventbox.connect("button_press_event", pressed)
    
    eventbox.connect_after("realize",
        lambda w: w.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2)))
    
    return eventbox



class GladeWidgets:
    """ A simple class that wraps a the glade get_widget function
        into the python __getitem__ version """
    def __init__ (self, filename):
        self.widgets = gtk.glade.XML(addDataPrefix("glade/%s" % filename))
    def __getitem__(self, key):
        return self.widgets.get_widget(key)


