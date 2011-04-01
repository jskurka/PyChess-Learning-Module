import gtk, cairo
import gobject

from OverlayWindow import OverlayWindow

from __init__ import NORTH, EAST, SOUTH, WEST

class ArrowButton (OverlayWindow):
    """ Leafs will connect to the drag-drop signal """
    
    __gsignals__ = {
        'dropped' : (gobject.SIGNAL_RUN_FIRST, None, (object,)),
        'hovered' : (gobject.SIGNAL_RUN_FIRST, None, (object,)),
        'left' : (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, parent, svgPath, position):
        OverlayWindow.__init__(self, parent)
        
        self.myparent = parent
        self.myposition = position
        self.svgPath = svgPath
        self.connect_after("expose-event", self.__onExposeEvent)
        
        targets = [("GTK_NOTEBOOK_TAB", gtk.TARGET_SAME_APP, 0xbadbeef)]
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           targets, gtk.gdk.ACTION_MOVE)
        self.drag_dest_set_track_motion(True)
        self.connect("drag-motion", self.__onDragMotion)
        self.connect("drag-leave", self.__onDragLeave)
        self.connect("drag-drop", self.__onDragDrop)
        
        self.hovered = False
        
        self.myparentAlloc = None
        self.myparentPos = None
        self.hasHole = False
    
    def _calcSize (self):
        parentAlloc = self.myparent.get_allocation()
        width, height = self.getSizeOfSvg(self.svgPath)
        
        if self.myparentAlloc == None:
            self.resize(width, height)
        
        if self.window and not self.hasHole:
            self.hasHole = True
            self.digAHole(self.svgPath, width, height)
        
        if self.myposition == NORTH:
            x, y = parentAlloc.width/2.-width/2., 0
        elif self.myposition == EAST:
            x, y = parentAlloc.width-width, parentAlloc.height/2.-height/2.
        elif self.myposition == SOUTH:
            x, y = parentAlloc.width/2.-width/2., parentAlloc.height-height
        elif self.myposition == WEST:
            x, y = 0, parentAlloc.height/2.-height/2.
        
        x, y = self.translateCoords(int(x), int(y))
        if (x,y) != self.get_position():
            self.move(x, y)
        
        self.myparentAlloc = parentAlloc
        self.myparentPos = self.myparent.window.get_position()
    
    def __onExposeEvent (self, self_, event):
        self._calcSize()
        context = self.window.cairo_create()
        width, height = self.getSizeOfSvg(self.svgPath)
        surface = self.getSurfaceFromSvg(self.svgPath, width, height)
        
        if self.is_composited():
            context.set_operator(cairo.OPERATOR_CLEAR)
            context.set_source_rgba(0.0,0.0,0.0,0.0)
            context.paint()
            context.set_operator(cairo.OPERATOR_OVER)
        
        mask = gtk.gdk.Pixmap(None, width, height, 1)
        mcontext = mask.cairo_create()
        mcontext.set_source_surface(surface, 0, 0)
        mcontext.paint()
        self.window.shape_combine_mask(mask, 0, 0)
        
        context.set_source_surface(surface, 0, 0)
        context.paint()
    
    def __containsPoint (self, x, y):
        alloc = self.get_allocation()
        return 0 <= x < alloc.width and 0 <= y < alloc.height
    
    def __onDragMotion (self, arrow, context, x, y, timestamp):
        if not self.hovered and self.__containsPoint(x,y):
            self.hovered = True
            self.emit("hovered", context.get_source_widget())
        elif self.hovered and not self.__containsPoint(x,y):
            self.hovered = False
            self.emit("left")
    
    def __onDragLeave (self, arrow, context, timestamp):
        if self.hovered:
            self.hovered = False
            self.emit("left")
    
    def __onDragDrop (self, arrow, context, x, y, timestamp):
        if self.__containsPoint(x,y):
            self.emit("dropped", context.get_source_widget())
            context.finish(True, True, timestamp)
            return True
