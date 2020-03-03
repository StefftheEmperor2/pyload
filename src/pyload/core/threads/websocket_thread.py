from .clicknload_thread import BaseServerThread
from ..network.websocket import Websocket


class WebsocketServerThread(BaseServerThread):

    def __init__(self, manager):
        super().__init__(manager)
        self.websocket = None

    def setup(self):
        self.websocket = Websocket(self.m.pyload)
        core = self.m.pyload

    def serve(self):
        self.websocket.serve()

    def register_session(self, uuid, session):
        self.websocket.register_session(uuid, session)

    def stop(self):
        self.websocket.stop()
