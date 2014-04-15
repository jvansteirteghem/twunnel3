import sys
import os
sys.path.insert(0, os.path.abspath(".."))

import asyncio
from twunnel3 import local_proxy_server, logger
from examples import example

configuration = \
{
    "LOGGER":
    {
        "LEVEL": 3
    }
}

logger.configure(configuration)

loop = asyncio.get_event_loop()

configuration = \
{
    "PROXY_SERVERS": [],
    "LOCAL_PROXY_SERVER":
    {
        "TYPE": "SOCKS4",
        "ADDRESS": "127.0.0.1",
        "PORT": 8080
    }
}

socks4_server = loop.run_until_complete(local_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS":
    [
        {
            "TYPE": "SOCKS4",
            "ADDRESS": "127.0.0.1",
            "PORT": 8080,
            "ACCOUNT":
            {
                "NAME": ""
            }
        }
    ]
}

loop.call_later(5, example.create_connection, configuration)
loop.call_later(10, example.create_connection, configuration, True)
loop.call_later(15, socks4_server.close)
loop.call_later(20, loop.stop)
loop.run_forever()