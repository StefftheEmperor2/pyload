from json import dumps as json_dumps
class Connection:
    def __init__(self, websocket):
        self._websocket = websocket
        self._events = []

    def add_event(self, event):
        self._events.append(event)

    def pop_event(self):
        return self._events.pop()

    def has_event(self):
        return len(self._events) > 0

    def is_equal(self, websocket):
        return self._websocket is websocket

    def get_events(self):
        return self._events

    async def write(self, message, payload):
        await self._websocket.send(json_dumps({"message": message, "payload": payload}))
