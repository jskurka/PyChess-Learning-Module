from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, md5, imp
from threading import Thread

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.ThreadPool import pool
#from pychess.System.TaskQueue import TaskQueue
from pychess.System.Log import log
from pychess.System.SubProcess import SubProcess, searchPath
from pychess.System.prefix import addHomePrefix
from pychess.Utils.const import *
from CECPEngine import CECPEngine
from UCIEngine import UCIEngine

attrToProtocol = {
    "uci": UCIEngine,
    "cecp": CECPEngine
}

# TODO: Diablo, Amy and Amundsen
backup = """
<engines>
    <engine protocol="cecp" protover="2" binname="PyChess.py" />
    <engine protocol="cecp" protover="2" binname="gnuchess">
        <meta><country>us</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="gnome-gnuchess">
        <meta><country>us</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="crafty">
        <meta><country>us</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="faile">
        <meta><country>ca</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="phalanx">
        <meta><country>cz</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="sjeng">
        <meta><country>be</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="hoichess">
        <meta><country>de</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="boochess">
        <meta><country>de</country></meta></engine>
    
    <engine protocol="uci" protover="1" binname="glaurung">
        <meta><country>no</country></meta></engine>
    <engine protocol="uci" protover="1" binname="ShredderClassicLinux">
        <meta><country>de</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit_21_static"> 
        <meta><country>fr</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit">
        <meta><country>fr</country></meta></engine>
</engines>
"""

class EngineDiscoverer (GObject, Thread):
    
    __gsignals__ = {
        "discovering_started": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "engine_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "all_engines_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        self.xmlpath = addHomePrefix("engines.xml")
        
        try:
            self.dom = minidom.parse( self.xmlpath )
        except ExpatError, e:
            log.warn("engineNest: %s\n" % e)
            self.dom = minidom.parseString( backup )
        except IOError:
            self.dom = minidom.parseString( backup )
        
        self._engines = {}
    
    ############################################################################
    # XML methods                                                              #
    ############################################################################
    
    def _clearEngine (self, engine):
        for child in [n for n in engine.childNodes]:
            engine.removeChild(child)
    
    def _createElement (self, name, strvalue="", args=[]):
        element = self.dom.createElement(name)
        if strvalue:
            element.appendChild(self.dom.createTextNode(strvalue))
        for key, value in args:
            element.setAttribute(key, value)
        return element
    
    def _createOrReturn (self, parrent, tagname):
        tags = parrent.getElementsByTagName(tagname)
        if not tags:
            tag = self.dom.createElement(tagname)
            parrent.appendChild(tag)
            return tag
        return tags[0]
    
    def _hasChildByTagName (self, parrent, tagname):
        for c in parrent.childNodes:
            if c.nodeType == c.ELEMENT_NODE and \
               c.tagName == tagname:
                return True
        return False
    
    ############################################################################
    # Discover methods                                                         #
    ############################################################################
    
    def _findPath (self, binname):
        if binname == "PyChess.py":
            if "PYTHONPATH" in os.environ:
                path = os.path.abspath(os.environ["PYTHONPATH"])
                path = os.path.join(path, "pychess/Players/PyChess.py")
            else:
                path = os.path.dirname(imp.find_module("os")[1])
                path = os.path.join(path,
                        "site-packages/pychess/Players/PyChess.py")
            return path, searchPath("python"), ["-u", path]
        else:
            for dir in os.environ["PATH"].split(":"):
                path = os.path.join(dir, binname)
                if os.path.isfile(path):
                    if not os.access (path, os.R_OK):
                        log.warn("Could not read the file %s\n" % path)
                        continue
                    if not os.access (path, os.EX_OK):
                        log.warn("Could not execute the file %s\n" % path)
                        continue
                    return path, path, []
        return False
    
    def _handleUCIOptions (self, engine, ids, options):
        meta = self._createOrReturn(engine, "meta")
        
        for key, value in ids.iteritems():
            if key == "name" and not self._hasChildByTagName(meta,"name"):
                meta.appendChild(self._createElement("name", value))
            elif key == "author" and not self._hasChildByTagName(meta,"author"):
                meta.appendChild(self._createElement("author", value))
        
        optnode = self._createOrReturn(engine, "options")
        
        # We don't want to change preset values, but currently there are none,
        # so 'preset' should be an empty dict
        preset = dict([(child.getAttribute("name"),True) for child in \
                optnode.childNodes if child.nodeType == child.ELEMENT_NODE])
        
        for name, dic in options.iteritems():
            if name in preset: continue
            
            type = dic["type"]
            del dic["type"]
            
            args = [ ("name",name) ]
            for key, value in dic.iteritems():
                if key != "vars":
                    args.append( (key,value) )
            
            if type == "check":
                args2 = []
                for key, value in args:
                    if value == True: value = "true"
                    elif value == False: value = "false"
                    args2.append( (key,value) )
                node = self._createElement("check-option", args=args2)
            elif type == "string":
                if name == "UCI_EngineAbout":
                    # I don't know why UCI puts about in the options, but we
                    # still put it in the meta where it belongs
                    meta = self._createOrReturn(engine, "meta")
                    if not self._hasChildByTagName (meta, "about"):
                        about = self._createElement("about", dic["default"])
                        meta.appendChild(about)
                    continue
                node = self._createElement("string-option", args=args)
            elif type == "combo":
                node = self._createElement("combo-option", args=args)
                for value in dic["vars"]:
                    varNode = self._createElement("var", args=[("value",value)])
                    node.appendChild( varNode )
            elif type == "spin":
                args = [(k,str(v)) for k,v in args]
                node = self._createElement("spin-option", args=args)
            elif type == "button":
                node = self._createElement("button-option", args=args)
            
            optnode.appendChild(node)
        
        engine.appendChild(optnode)
    
    def _handleCECPOptions (self, engine, features):
        feature_node = self._createOrReturn(engine, "cecp-features")
        meta = self._createOrReturn(engine, "meta")
        
        # We don't want to change preset values, but currently there are
        # none, so 'preset' should be an empty dict
        preset = dict ([(f.getAttribute("command"), True) for f in \
                                feature_node.getElementsByTagName("feature")])
        
        for key, value in features.iteritems():
            if key in preset: continue
            
            if key == "myname":
                meta.appendChild( self._createElement("name", value) )
            
            args = (("command",key),
                    ("supports", value and "true" or "false"))
            node = self._createElement("feature",args=args)
            feature_node.appendChild(node)
        
        if not self._hasChildByTagName(engine, "options"):
            options = self.dom.createElement("options")
            options.appendChild(self._createElement("check-option", \
                                args=(("name","Ponder"), ("default","false"))))
            options.appendChild(self._createElement("check-option", \
                                args=(("name","Random"), ("default","false"))))
            options.appendChild(self._createElement("spin-option", \
                                args=(("name","Depth"), ("min","1"),
                                    ("max","-1"), ("default","false"))))
            engine.appendChild(options)
    
    def _findOutMore (self, toBeDiscovered):
        # List of engines which fails and must be rechecked another time
        rechecks = [] 
        
        # Test engines
        for xmlengine, binname in toBeDiscovered:
            engine = self.initEngine (xmlengine, BLACK)
            try:
                try:
                    engine.start(True)
                    protname = xmlengine.getAttribute("protocol")
                    if protname == "uci":
                        self._handleUCIOptions (xmlengine, engine.ids, engine.options)
                    elif protname == "cecp":
                        self._handleCECPOptions (xmlengine, engine.features)
                except:
                    rechecks.append(xmlengine)
            finally:
                exitcode = engine.kill(UNKNOWN_REASON)
                if exitcode:
                    rechecks.append(xmlengine)
                    log.debug("Engine failed %s\n" % self.getName(xmlengine))
                else:
                    log.debug("Engine finished %s\n" % self.getName(xmlengine))
                self.emit ("engine_discovered", binname, xmlengine)
        
        return rechecks
        
    ############################################################################
    # Main loop                                                                #
    ############################################################################
    
    def start (self):
        toBeDiscovered = []
        
        for engine in self.dom.getElementsByTagName("engine"):
            if not engine.hasAttribute("protocol") and \
                   engine.hasAttribute("binname"):
                continue
            
            binname = engine.getAttribute("binname")
            location = self._findPath(binname)
            
            if not location:
                # We ignore engines not available
                continue
            
            file, path, args = location
            md5sum = md5.new(open(file).read()).hexdigest()
            
            checkIt = False
            
            fileNodes = engine.getElementsByTagName("file")
            if fileNodes:
                efile = fileNodes[0].childNodes[0].data.split()[-1]
                if efile != file:
                    self._clearEngine(engine)
                    checkIt = True
                else:
                    md5Nodes = engine.getElementsByTagName("md5")
                    if not md5Nodes or \
                            md5Nodes[0].childNodes[0].data.strip() != md5sum:
                        self._clearEngine(engine)
                        checkIt = True
            else:
                checkIt = True
            
            if checkIt:
                engine.appendChild( self._createElement("file", file) )
                engine.appendChild( self._createElement("path", path) )
                argselem = engine.appendChild( self._createElement("args") )
                for arg in args:
                    typestr = repr(type(arg))[7:-2]
                    elem = self._createElement("arg", str(arg), (("type", typestr),))
                    argselem.appendChild(elem)
                engine.appendChild( self._createElement("md5", md5sum) )
                toBeDiscovered.append((engine, binname))
            
            self._engines[binname] = engine
        
        if toBeDiscovered:
            self.emit("discovering_started", 
                [binname for engine, binname in toBeDiscovered])
            rechecks = self._findOutMore(toBeDiscovered)
            for xmlengine in rechecks:
                md5Nodes = xmlengine.getElementsByTagName("md5")
                xmlengine.removeChild(md5Nodes[0])
        
        self.emit("all_engines_discovered")
        
        try:
            f = open(self.xmlpath, "w")
            self.dom.writexml(f)
            f.close()
        except IOError, e:
            log.warn("Saving enginexml raised exception: %s\n" % \
                    ", ".join(str(a) for a in e.args))
    
    ############################################################################
    # Interaction                                                              #
    ############################################################################
    
    def getAnalyzers (self):
        engines = self.getEngines()
        analyzers = []
        for engine in engines.values():
            protocol = engine.getAttribute("protocol")
            if protocol == "uci":
                analyzers.append(engine)
            elif protocol == "cecp":
                for feature in engine.getElementsByTagName("feature"):
                    if feature.getAttribute("command") == "analyze":
                        if feature.getAttribute("supports") == "true":
                            analyzers.append(engine)
                        break
        return analyzers
    
    def getEngines (self):
        """ Returns {binname: enginexml} """
        return self._engines
    
    def getEngineN (self, index):
        return self.getEngines()[self.getEngines().keys()[index]]
    
    def getEngineByMd5 (self, md5sum, list=[]):
        if not list:
            list = self.getEngines().values()
        for engine in list:
            md5s = engine.getElementsByTagName("md5")
            if not md5s: continue
            md5 = md5s[0]
            if md5.childNodes[0].data.strip() == md5sum:
                return engine
    
    def getName (self, engine=None):
        # Test if the call was to get the name of the thread
        if engine == None:
            return Thread.getName(self)
        names = engine.getElementsByTagName("name")
        if names:
            return names[0].childNodes[0].data.strip()
        else:
            return engine.getAttribute("binname")
    
    def getCountry (self, engine):
        c = engine.getElementsByTagName("country")
        if c:
            return c[0].childNodes[0].data.strip()
        return None
    
    def getArgs (self, engine):
        args = []
        for arg in engine.getElementsByTagName("arg"):
            type = arg.getAttribute("type")
            value = arg.childNodes[0].data.strip()
            if type == "bool":
                args.append(value.lower() == "true" and True or False)
            else:
                args.append(__builtins__[type](value))
        return args
   
    def initEngine (self, xmlengine, color):
        protover = int(xmlengine.getAttribute("protover"))
        protocol = xmlengine.getAttribute("protocol")
        
        path = xmlengine.getElementsByTagName("path")[0].childNodes[0].data.strip()
        args = self.getArgs(xmlengine)
        warnwords = ("illegal", "error")
        subprocess = SubProcess(path, args, warnwords, SUBPROCESS_SUBPROCESS)
        
        return attrToProtocol[protocol](subprocess, color, protover)
    
    #
    # Other
    #
    
    def __del__ (self):
        self.dom.unlink()

discoverer = EngineDiscoverer()
discoverer.start()

if __name__ == "__main__":

    discoverer = EngineDiscoverer()

    def discovering_started (discoverer, list):
        print "discovering_started", list
    discoverer.connect("discovering_started", discovering_started)

    from threading import RLock
    rlock = RLock()

    def engine_discovered (discoverer, str, object):
        rlock.acquire()
        try:
            print "engine_discovered", str, object.toprettyxml()
        finally:
            rlock.release()
    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered (discoverer):
        print "all_engines_discovered"
    discoverer.connect("all_engines_discovered", all_engines_discovered)

    discoverer.start()
    discoverer.getEngines()
