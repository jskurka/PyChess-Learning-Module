# -*- coding: UTF-8 -*-

import gtk
import pango

import time

from pychess.System import uistuff
from pychess.System.Log import log
from pychess.Utils.const import LOCAL, WHITE, BLACK
from pychess.widgets.ChatView import ChatView

__title__ = _("Chat")

class Sidepanel:
    def load (self, gmwidg):
        self.chatView = ChatView()
        self.chatView.disable("Waiting for game to load")
        self.chatView.connect("messageTyped", self.onMessageSent)
        self.gamemodel = gmwidg.gamemodel
        self.gamemodel.connect("game_started", self.onGameStarted)
        return self.chatView
    
    def onGameStarted (self, gamemodel):
        if gamemodel.players[0].__type__ == LOCAL:
            self.player = gamemodel.players[0]
            self.opplayer = gamemodel.players[1]
            if gamemodel.players[1].__type__ == LOCAL:
                log.warn("Chatpanel loaded with two local players")
        elif gamemodel.players[1].__type__ == LOCAL:
            self.player = gamemodel.players[1]
            self.opplayer = gamemodel.players[0]
        else:
            log.warn("Chatpanel loaded with no local players")
        self.player.connect("messageRecieved", self.onMessageReieved)
        
        self.chatView.enable()
    
    def onMessageReieved (self, player, text):
        self.chatView.addMessage(repr(self.opplayer), text)
    
    def onMessageSent (self, chatView, text):
        self.player.sendMessage(text)
        self.chatView.addMessage(repr(self.player), text)
