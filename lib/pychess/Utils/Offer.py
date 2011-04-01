from pychess.Utils.const import ACTIONS

class Offer:
    def __init__(self, type_, param=None, index=None):
        assert type_ in ACTIONS, "Offer.__init__(): type not in ACTIONS: %s" % repr(type_)
        assert index is None or type(index) is int, \
            "Offer.__init__(): index not int: %s" % repr(index)
        self.type = type_
        self.param = param
        self.index = index  # for IC games
    
    def __hash__(self):
        return hash((self.type, self.param, self.index))
    
    def __cmp__(self, other):
        assert type(other) is type(self), "Offer.__cmp__(): not of type Offer: %s" % repr(other)
        return cmp(hash(self), hash(other))
    
    def __repr__(self):
        s = "type=\"%s\"" % self.type
        if self.param is not None:
            s += ", param=%s" % str(self.param)
        if self.index is not None:
            s += ", index=%s" % str(self.index)
        return "Offer(" + s + ")"
