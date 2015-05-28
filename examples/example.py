import asyncio
import twunnel3.logger
import twunnel3.proxy_server

class Protocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("trace: Protocol.__init__")
        
        self.request = b""
        self.response = b""
        
    def connection_made(self, transport):
        twunnel3.logger.trace("trace: Protocol.connection_made")
        
        self.transport = transport
        
        self.request = b"HEAD / HTTP/1.1\r\n"
        
        if self.factory.port == 80 or self.factory.port == 443:
            self.request = self.request + b"Host: " + self.factory.address.encode() + b"\r\n"
        else:
            self.request = self.request + b"Host: " + self.factory.address.encode() + b":" + str(self.factory.port).encode() + b"\r\n"
        
        self.request = self.request + b"\r\n"
        
        twunnel3.logger.info("request: " + self.request.decode())
        
        self.transport.write(self.request)
    
    def connection_lost(self, exception):
        twunnel3.logger.trace("trace: Protocol.connection_lost")
        
        self.transport = None
        
    def data_received(self, data):
        twunnel3.logger.trace("trace: Protocol.data_received")
        
        self.response = self.response + data
        
        i = self.response.find(b"\r\n\r\n")
        
        if i == -1:
            return
        
        twunnel3.logger.info("response: " + self.response.decode())
        
        self.transport.close()
        
class ProtocolFactory(object):
    def __init__(self):
        twunnel3.logger.trace("trace: ProtocolFactory.__init__")
        
        self.address = ""
        self.port = 0
    
    def __call__(self):
        twunnel3.logger.trace("trace: ProtocolFactory.__call__")
        
        protocol = Protocol()
        protocol.factory = self
        return protocol

def create_connection(configuration, ssl=False):
    factory = ProtocolFactory()
    factory.address = "www.google.com"
    
    if ssl == False:
        factory.port = 80
    else:
        factory.port = 443
    
    tunnel = twunnel3.proxy_server.create_tunnel(configuration)
    asyncio.async(tunnel.create_connection(factory, address=factory.address, port=factory.port, ssl=ssl))