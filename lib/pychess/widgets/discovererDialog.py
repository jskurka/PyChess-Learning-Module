from Throbber import Throbber
from pychess.Players.engineNest import discoverer
from pychess.System import conf, uistuff
from pychess.System.glock import glock_connect
from pychess.System.prefix import addDataPrefix
import gtk.glade
import os

 


uistuff.cacheGladefile("discovererDialog.glade")

class DiscovererDialog:
    
    @classmethod
    def init (cls, discoverer):
        assert not hasattr(cls, "widgets"), "Show can only be called once"
        cls.widgets = uistuff.GladeWidgets("discovererDialog.glade")
        
        #=======================================================================
        # Clear glade defaults
        #=======================================================================
        for child in cls.widgets["enginesTable"].get_children():
            cls.widgets["enginesTable"].remove(child)
        
        #=======================================================================
        # Connect us to the discoverer
        #=======================================================================
        glock_connect(discoverer, "discovering_started", cls._onDiscoveringStarted)
        glock_connect(discoverer, "engine_discovered", cls._onEngineDiscovered)
        glock_connect(discoverer, "all_engines_discovered", cls._onAllEnginesDiscovered)
        cls.finished = False
    
    @classmethod
    def show (cls, discoverer, mainwindow):
        if cls.finished:
            return
        
        #=======================================================================
        # Add throbber
        #=======================================================================
        
        throbber = Throbber(100, 100)
        throbber.set_size_request(100, 100)
        cls.widgets["throbberDock"].add(throbber)
        
        #=======================================================================
        # Show the window
        #=======================================================================
        cls.widgets["discovererDialog"].set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        cls.widgets["discovererDialog"].set_modal(True)
        cls.widgets["discovererDialog"].set_transient_for(mainwindow)
        cls.widgets["discovererDialog"].show_all()
    
    @classmethod
    def _onDiscoveringStarted (cls, discoverer, binnames):
        #======================================================================
        # Insert the names to be discovered
        #======================================================================
        cls.nameToBar = {}
        for i, name in enumerate(binnames):
            label = gtk.Label(name+":")
            label.props.xalign = 1
            cls.widgets["enginesTable"].attach(label, 0, 1, i, i+1)
            bar = gtk.ProgressBar()
            cls.widgets["enginesTable"].attach(bar, 1, 2, i, i+1)
            cls.nameToBar[name] = bar
    
    @classmethod
    def _onEngineDiscovered (cls, discoverer, binname, xmlenginevalue):
        bar = cls.nameToBar[binname]
        bar.props.fraction = 1
    
    @classmethod
    def _onAllEnginesDiscovered (cls, discoverer):
        cls.finished = True
        cls.widgets["discovererDialog"].hide()
