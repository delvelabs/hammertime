# HammerTime: HTTP client library for pentest tools

## Features
* Can perform a large number of requests as fast as the server can take them.
* Includes heuristics to discard invalid responses.
* Soft-404 detection
* Proxy support
* Dynamic timeout
* Support to add custom heuristics


## Installation
HammerTime requires python 3.5.2
```bash
pip install hammertime-http
```


## Optional Dependancies
* simhash-py (c++ implementation) as a faster alternative to simhash. A compiler is required for the 
installation. Note that simhash is only used for soft-404 detection.
* uvloop for a faster implementation of asyncio event loop.


## Getting started

To send a large number of requests in parallel and retrieve them as soon as they are done:

```python
from hammertime import HammerTime

# Import required heuristics:
from hammertime.rules import DynamicTimeout, RejectStatusCode

hammertime = HammerTime()

#To add a single heuristic:
reject_404 = RejectStatusCode([404])
hammertime.heuristics.add(reject_404)

#To add multiple heuristics:
reject_5xx = RejectStatusCode(range(500, 600))
timeout = DynamicTimeout(min_timeout=0.01, max_timeout=1, retries=3)
hammertime.heuristics.add_multiple([reject_5xx, timeout])

async def fetch():
    for i in range(10000):
        hammertime.request("http://example.com/")
    async for entry in hammertime.successful_requests():
        pass
    
hammertime.loop.run_until_complete(fetch())
```

Note that only the entry of successful requests are returned, and no exception are raised when a request fails 
or is rejected.

HammerTime.request returns the request wrapped in a asyncio.Task, so you can await for the completion of all requests:

```python
import asyncio
from hammertime import HammerTime

hammertime = HammerTime()

async def fetch():
    tasks = []
    for i in range(10000):
        tasks.append(hammertime.request("http://example.com/"))
    done, pending = await asyncio.wait(tasks, loop=hammertime.loop, return_when=asyncio.ALL_COMPLETED)
    for future in done:
        entry = await future
    
hammertime.loop.run_until_complete(fetch())
```
With this method, HammerTime exceptions are raised when awaiting the future containing a request if that request failed 
or was rejected.

You can also wait for a single request to complete and get its result:

```python
from hammertime import HammerTime

hammertime = HammerTime()

async def fetch():
    entry = await hammertime.request("http://example.com/")

hammertime.loop.run_until_complete(fetch())
```
This method also raises HammerTime exceptions if the request fails or is rejected.

HammerTime can retry a failed request if a retry count is specified (default is 0, or no retry):

```python
hammertime = HammerTime(retry_count=3)
```
This will make HammerTime abandon a request after the fourth attempt (initial request + 3 retries).
