import websockets
import asyncio
from .connection import Connection
from time import sleep
from json import dumps as json_dumps, loads as json_loads
from uuid import uuid1
class Websocket:
    def __init__(self, core):
        self.core = core
        self.event_manager_client_id = uuid1()
        self.connections = set()
        self.sessions = {}
        self.event_loop = asyncio.get_event_loop()
        self.event_loop.set_debug(bool(core.debug))
        start_server = websockets.serve(self.handler, core.config.get("webui", "host"), core.config.get("webui", "websocket_port"))
        asyncio.get_event_loop().run_until_complete(start_server)

    def serve(self):
        self.event_loop.run_forever()

    def stop(self):
        self.event_loop.stop()

    def register_session(self, uuid, session):
        self.sessions[uuid] = {
            "role": session.get("role"),
            "perms": session.get("perms")
        }

    async def register(self, websocket):
        self.connections.add(Connection(websocket))

    async def unregister(self, websocket):
        for connection in self.connections:
            if connection.is_equal(websocket):
                self.connections.remove(connection)
                break

    async def consumer_handler(self, websocket, path):
        try:
            async for message in websocket:
                message_data = json_loads(message)

                sleep(1)
        except Exception as exc:
            if not isinstance(exc, asyncio.CancelledError):
                self.core.log.error(exc)

    async def producer_handler(self, websocket, path):
        events = self.core.event_manager.get_events(self.event_manager_client_id)
        active_connection = None
        for connection in self.connections:
            if connection.is_equal(websocket):
                active_connection = connection
            for event in events:
                connection.add_event(event)

        if active_connection is not None:
            while active_connection.has_event():
                event = active_connection.pop_event()
                try:
                    if len(event) is 4 and event[:3] == ('update', 'queue', 'file'):
                        file = self.core.file_manager.get_file(event[3])
                        await active_connection.write('update_queue_file', file.get_json())
                    elif len(event) is 4 and event[:3] == ('update', 'queue', 'pack'):
                        package = self.core.file_manager.get_package(event[3])
                        await active_connection.write('update_queue_pack', package.get_json())
                    elif len(event) is 1 and event[0] == 'core':
                        await active_connection.write('update_core', self.core.get_json())
                    else:
                        pass
                except websockets.exceptions.ConnectionClosedOK:
                    await self.unregister(websocket)
                except Exception as exc:
                    if not isinstance(exc, asyncio.CancelledError):
                        self.core.log.error(exc)


    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            while True:
                consumer_task = asyncio.ensure_future(
                    self.consumer_handler(websocket, path))
                producer_task = asyncio.ensure_future(
                    self.producer_handler(websocket, path))
                done, pending = await asyncio.wait(
                    [consumer_task, producer_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
        except Exception as exc:
           self.core.log.error(exc)
        finally:
            await self.unregister(websocket)
