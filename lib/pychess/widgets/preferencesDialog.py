import sys, os

import gtk, gobject

from pychess.System.prefix import prefix
from pychess.System import conf, gstreamer, uistuff
from pychess.Utils.const import *
from pychess.Players.engineNest import discoverer

firstRun = True
def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["preferences"].show()

def initialize(widgets):
    
    def delete_event (widget, *args):
        widgets["preferences"].hide()
        return True
    
    GeneralTab(widgets)
    EngineTab(widgets)
    SoundTab(widgets)
    
    widgets["preferences"].connect("delete-event", delete_event)
    widgets["preferences_close_button"].connect("clicked", delete_event)

################################################################################
# General initing                                                              #
################################################################################

class GeneralTab:
    
    def __init__ (self, widgets):
        
        conf.set("firstName", conf.get("firstName", username))
        conf.set("secondName", conf.get("secondName", _("Guest")))
        
        # Give to uistuff.keeper
        
        for key in ("firstName", "secondName",
                    "hideTabs", "autoRotate", "showCords", "figuresInNotation",  
                    "fullAnimation", "moveAnimation", "noAnimation"):
            uistuff.keep(widgets[key], key)

################################################################################
# Engine initing                                                               #
################################################################################

class EngineTab:
    
    def __init__ (self, widgets):
        
        # Put engines in trees and combos
        
        engines = discoverer.getEngines()
        allstore = gtk.ListStore(gtk.gdk.Pixbuf, str)
        for engine in engines.values():
            c = discoverer.getCountry(engine)
            if c:
                flag = "flags/%s.png" % c
            else: flag = "flags/unknown.png"
            flag_icon = gtk.gdk.pixbuf_new_from_file(prefix(flag))
            allstore.append((flag_icon, discoverer.getName(engine)))
        
        tv = widgets["engines_treeview"]
        tv.set_model(allstore)
        tv.append_column(gtk.TreeViewColumn(
                "Flag", gtk.CellRendererPixbuf(), pixbuf=0))
        tv.append_column(gtk.TreeViewColumn(
                "Name", gtk.CellRendererText(), text=1))
        
        analyzers = discoverer.getAnalyzers()
        ana_data = []
        invana_data = []
        for engine in analyzers:
            name = discoverer.getName(engine)
            c = discoverer.getCountry(engine)
            if c:
                flag = "flags/%s.png" % c
            else: flag = "flags/unknown.png"
            flag_icon = gtk.gdk.pixbuf_new_from_file(prefix(flag))
            ana_data.append((flag_icon, name))
            invana_data.append((flag_icon, name))
        
        uistuff.createCombo(widgets["ana_combobox"], ana_data)
        uistuff.createCombo(widgets["inv_ana_combobox"], invana_data)
        
        # Save, load and make analyze combos active
        
        conf.set("ana_combobox", conf.get("ana_combobox", 0))
        conf.set("inv_ana_combobox", conf.get("inv_ana_combobox", 0))
        
        def on_analyzer_check_toggled (check):
            widgets["analyzers_vbox"].set_sensitive(check.get_active())
            widgets["hint_mode"].set_active(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                widgets["hint_mode"].set_sensitive(check.get_active())
        widgets["analyzer_check"].connect("toggled", on_analyzer_check_toggled)
        uistuff.keep(widgets["analyzer_check"], "analyzer_check")
        
        def on_analyzer_check_toggled (check):
            widgets["inv_analyzers_vbox"].set_sensitive(check.get_active())
            widgets["spy_mode"].set_active(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                widgets["spy_mode"].set_sensitive(check.get_active())
        widgets["inv_analyzer_check"].connect("toggled", on_analyzer_check_toggled)
        uistuff.keep(widgets["inv_analyzer_check"], "inv_analyzer_check")
        
        # Put options in trees in add/edit dialog
        
        tv = widgets["optionview"]
        tv.append_column(gtk.TreeViewColumn(
            "Option", gtk.CellRendererText(), text=0))
        tv.append_column(gtk.TreeViewColumn(
            "Value", gtk.CellRendererText(), text=1))
        
        def edit (button):
            
            iter = widgets["engines_treeview"].get_selection().get_selected()[1]
            if iter: row = allstore.get_path(iter)[0]
            else: return
            
            engine = discoverer.getEngineN(row)
            optionstags = engine.getElementsByTagName("options")
            if not optionstags:
                widgets["engine_options_expander"].hide()
            else:
                widgets["engine_options_expander"].show()
                widgets["engine_options_expander"].set_expanded(False)
                
                optionsstore = gtk.ListStore(str, str)
                tv = widgets["optionview"]
                tv.set_model(optionsstore)
                
                for option in optionstags[0].childNodes:
                    if option.nodeType != option.ELEMENT_NODE: continue
                    optionsstore.append( [option.getAttribute("name"),
                                          option.getAttribute("default")] )
                
            widgets["engine_path_chooser"].set_title(_("Locate Engine"))
            widgets["engine_path_chooser"].set_uri("file:///usr/bin/gnuchess")
            
            dialog = widgets["addconfig_engine"]
            answer = dialog.run()
            dialog.hide()
        widgets["edit_engine_button"].connect("clicked", edit)
        #widgets["remove_engine_button"].connect("clicked", remove)
        #widgets["add_engine_button"].connect("clicked", add)
        
        # Give widgets to kepper
        
        for combo in ("ana_combobox", "inv_ana_combobox"):
            
            def get_value (combobox):
                engine = discoverer.getAnalyzers()[combobox.get_active()]
                md5s = engine.getElementsByTagName("md5")
                if md5s:
                    return md5s[0].childNodes[0].data.strip()
            
            def set_value (combobox, value):
                engine = discoverer.getEngineByMd5(value)
                if not engine:
                    combobox.set_active(0)
                else:
                    try:
                        index = discoverer.getAnalyzers().index(engine)
                    except ValueError:
                        index = 0
                    combobox.set_active(index)
            
            uistuff.keep (widgets[combo], combo, get_value, set_value)
        
################################################################################
# Sound initing                                                                #
################################################################################

class SoundTab:
    
    SOUND_DIRS = ("/usr/share/sounds", "/usr/local/share/sounds",
                  os.environ["HOME"])
    
    COUNT_OF_SOUNDS = 9
    
    actionToKeyNo = {
        "aPlayerMoves": 0,
        "aPlayerChecks": 1,
        "aPlayerCaptures": 2,
        "gameIsSetup": 3,
        "gameIsWon": 4,
        "gameIsLost": 5,
        "gameIsDrawn": 6,
        "observedMoves": 7,
        "oberservedEnds": 8
    }
    
    @classmethod
    def playAction (cls, action):
        if type(action) == str:
            no = cls.actionToKeyNo[action]
        else: no = action
        typ = conf.get("soundcombo%d" % no, SOUND_MUTE)
        if typ == SOUND_BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif typ == SOUND_URI:
            uri = conf.get("sounduri%d" % no, "")
            if not os.path.isfile(uri[7:]):
                conf.set("soundcombo%d" % no, SOUND_MUTE)
                return
            gstreamer.playSound(uri)
    
    def __init__ (self, widgets):
        
        # Init open dialog
        
        opendialog = gtk.FileChooserDialog (
                _("Open Sound File"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
                 (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN,
                  gtk.RESPONSE_ACCEPT))
        
        for dir in self.SOUND_DIRS:
            if os.path.isdir(dir):
                opendialog.set_current_folder(dir)
                break
        
        soundfilter = gtk.FileFilter()
        soundfilter.add_custom(soundfilter.get_needed(),
                               lambda data: data[3].startswith("audio/"))
        opendialog.add_filter(soundfilter)
        opendialog.set_filter(soundfilter)
        
        # Get combo icons
        
        icons = ((_("No sound"), "audio-volume-muted", "audio-volume-muted"),
                 (_("Beep"), "stock_bell", "audio-x-generic"), 
                 (_("Select sound file..."), "gtk-open", "document-open"))
        
        it = gtk.icon_theme_get_default()
        items = []
        for level, stock, altstock in icons:
            try:
                image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
            except gobject.GError:
                image = it.load_icon(altstock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
            items += [(image, level)]
        
        audioIco = it.load_icon("audio-x-generic", 16,
                                gtk.ICON_LOOKUP_USE_BUILTIN)
        
        # Set-up combos
        
        def callback (combobox, index):
            if combobox.get_active() == SOUND_SELECT:
                if opendialog.run() == gtk.RESPONSE_ACCEPT:
                    uri = opendialog.get_uri()
                    model = combobox.get_model()
                    conf.set("sounduri%d"%index, uri)
                    label = os.path.split(uri)[1]
                    if len(model) == 3:
                        model.append([audioIco, label])
                    else:
                        model.set(model.get_iter((3,)), 1, label)
                    combobox.set_active(3)
                else:
                    combobox.set_active(conf.get("soundcombo%d"%index,SOUND_MUTE))
                opendialog.hide()
        
        for i in xrange(self.COUNT_OF_SOUNDS):
            combo = widgets["soundcombo%d"%i]
            uistuff.createCombo (combo, items)
            combo.set_active(0)
            combo.connect("changed", callback, i)
            
            label = widgets["soundlabel%d"%i]
            label.props.mnemonic_widget = combo
            
            uri = conf.get("sounduri%d"%i,"")
            if os.path.isfile(uri[7:]):
                model = combo.get_model()
                model.append([audioIco, os.path.split(uri)[1]])
                combo.set_active(3)
            
        for i in xrange(self.COUNT_OF_SOUNDS):
            if conf.get("soundcombo%d"%i, SOUND_MUTE) == SOUND_URI and \
                    not os.path.isfile(conf.get("sounduri%d"%i,"")[7:]):
                conf.set("soundcombo%d"%i, SOUND_MUTE)
            uistuff.keep(widgets["soundcombo%d"%i], "soundcombo%d"%i)
        
        # Init play button
        
        def playCallback (button, index):
            SoundTab.playAction(index)
        
        for i in range (self.COUNT_OF_SOUNDS):
            button = widgets["soundbutton%d"%i]
            button.connect("clicked", playCallback, i)
        
        # Init 'use sound" checkbutton
        
        def checkCallBack (*args):
            checkbox = widgets["useSounds"]
            widgets["frame23"].set_property("sensitive", checkbox.get_active())
        conf.notify_add("useSounds", checkCallBack)
        uistuff.keep(widgets["useSounds"], "useSounds")
        checkCallBack()
