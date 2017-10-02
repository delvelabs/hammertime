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

To send a large number of requests in parallel and get each response as soon as the request is done:

```python
from hammertime import HammerTime

# Import required heuristics:
from hammertime.rules import DynamicTimeout, RejectStatusCode

hammertime = HammerTime(retry_count=3)  # Retries for failed request (default is 0, or no retry)

#To add multiple heuristics:
reject_5xx = RejectStatusCode(range(500, 600))
timeout = DynamicTimeout(min_timeout=0.01, max_timeout=1, retries=3)
hammertime.heuristics.add_multiple([reject_5xx, timeout])

hammertime.collect_successful_requests()

async def fetch():
    for i in range(10000):
        hammertime.request("http://example.com/")
    async for entry in hammertime.successful_requests():
        pass
    
hammertime.loop.run_until_complete(fetch())
```

Note that only the entry of successful requests are returned, and no exception are raised when a request fails 
or is rejected.

HammerTime.request returns the request wrapped in a asyncio.Task, so you can await for the completion of all requests, 
or wait for a single request:

```python
import asyncio
from hammertime import HammerTime
from hammertime.rules import RejectStatusCode


hammertime = HammerTime()

#To add a single heuristic:
reject_404 = RejectStatusCode([404])
hammertime.heuristics.add(reject_404)

async def fetch():
    tasks = []
    for i in range(10000):
        tasks.append(hammertime.request("http://example.com/"))
    done, pending = await asyncio.wait(tasks, loop=hammertime.loop, 
                                       return_when=asyncio.ALL_COMPLETED)
    for future in done:
        entry = await future
    
    # Wait for a single request:
    entry = await hammertime.request("http://example.com/")
    
hammertime.loop.run_until_complete(fetch())
```
When awaiting Hammertime.requests or the future wrapping the entry, an HammerTime exception is raised if the request
failed or was rejected.
