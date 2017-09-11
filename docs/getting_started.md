# HammerTime: HTTP client library for pentest tools

## Features
* Can perform a large number of requests as fast as the server can take them.
* Includes heuristics to discard invalid responses.
* Soft-404 detection
* Proxy support
* Dynamic timeout
* Support to add custom heuristics

## Installation
```bash
pip install hammertime-http
```

## Dependancies
* Python 3.5.2
* aiohttp 2.0.5
* aiodns
* easyinject 0.3
* simhash
* Optional simhash-py (c++ implementation) as a faster alternative to simhash. A compiler is required for the 
installation. Note that simhash is only used for soft-404 detection.


## Getting started

To send a large number of requests in parallel and retrieve them as soon as they are done:

```python
from hammertime import HammerTime

hammertime = HammerTime()

async def fetch():
    for i in range(10000):
        hammertime.request("http://example.com/")
    async for entry in hammertime.successful_requests():
        pass
    
hammertime.loop.run_until_complete(fetch())
```

HammerTime.request returns the request wrapped in a asyncio.Task, so you can await for the completion of all requests:

```python
import asyncio
from hammertime import HammerTime

hammertime = HammerTime()

async def fetch():
    tasks = []
    for i in range(10000):
        tasks.append(hammertime.request("http://example.com/"))
    entries = await asyncio.wait(tasks, loop=hammertime.loop, return_when=asyncio.ALL_COMPLETED)
    for entry in entries:
        pass
    
hammertime.loop.run_until_complete(fetch())
```

Or wait for a single request to complete and get its result:

```python
from hammertime import HammerTime

hammertime = HammerTime()

async def fetch():
    entry = await hammertime.request("http://example.com/")

hammertime.loop.run_until_complete(fetch())
```

HammerTime can retry a failed request if a retry count is specified (default is 0, or no retry). This will make 
HammerTime abandon a request after the fourth attempt (initial request + 3 retries):

```python
hammertime = HammerTime(retry_count=3)
```

## Proxy support

To send http requests over a proxy, pass the address of the proxy to HammerTime:

```python
hammertime = HammerTime(proxy="http://127.0.0.1/:8080")
```

or use the set_proxy method:

```python
hammertime = HammerTime()
hammertime.set_proxy("http://127.0.0.1/:8080")
 ```

to send https requests over a proxy, pass an instance of an AioHttpEngine to HammerTime, with ssl authentication 
disabled (not recommended) or the CA certificate of the proxy (recommended):

```python
from hammertime.engine.aiohttp import AioHttpEngine
from hammertime.config import custom_event_loop
from hammertime import HammerTime

loop = custom_event_loop()
engine = AioHttpEngine(loop=loop, verify_ssl=False, proxy="http://127.0.0.1/:8080")
# or
engine = AioHttpEngine(loop=loop, ca_certificate_file="path/to/proxy/cert.pem", proxy="http://127.0.0.1/:8080")
hammertime = HammerTime(request_engine=engine)
```

## Contributing

## Authors and License

