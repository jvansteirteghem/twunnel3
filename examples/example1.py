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
    "PROXY_SERVERS":
    [
    ]
}

loop.call_later(5, example.create_connection, configuration)
loop.call_later(10, example.create_connection, configuration, True)
loop.call_later(15, loop.stop)
loop.run_forever()