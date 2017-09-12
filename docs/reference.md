# HammerTime Reference


## HammerTime class

**class hammertime.HammerTime(loop=loop, request_engine=request_engine, kb=kb, retry_count=0, proxy=None)**

The core class of HammerTime to make requests

Parameters:  
* **loop**: Event loop used by HammerTime. By default, it is uvloop if available, else asyncio event loop is
            used. Except if a custom loop is required, you don't need to pass a loop to HammerTime, as the injector 
            automatically initialize HammerTime with a default loop.
* **request_engine**: The [AioHttpEngine](#aiohttpengine-class) used to make the HTTP requests. The injector pass a 
                      AioHttpEngine automatically. A custom instance can be provided if the default values are not 
                      suitable.
* **kb**: The knowledge base used by the heuristics. The injector creates an empty knowledge base by default.
* **retry_count**: The amount of time HammerTime will send a request after the initial attempt failed. A retry count of 
                   3 means that a single request can be sent up to 4 times (the inital attempt + 3 retries). Default is
                   0 (no retry).
* **proxy**: The HTTP proxy used to send the requests. Must be a string containing the proxy URL. Default is none 
             (no proxy).
                
**attribute hammertime.HammerTime.loop**

The event loop used by HammerTime.
    
**attribute hammertime.HammerTime.stats**

A [Stats](#stats-class) instance containing the statistics about HammerTime requests (duration, rate, retry count, 
success count, etc.)

**attribute hammertime.HammerTime.request_engine**

The [RetryEngine](#retryengine-class) instance used by HammerTime to make the requests.
    
**attribute hammertime.HammerTime.heuristics**

A Heuristics instance containing the heuristics used by HammerTime.
    
**attribute hammertime.HammerTime.completed_queue**

A asyncio.Queue containing the entries of the successful requests.
    
**attribute hammertime.HammerTime.tasks**

A collections.deque containing the pending requests (wrapped in asyncio.Tasks).

**attribute hammertime.HammerTime.closed**

An asyncio.Future used to wait for the completion of the close process of HammerTime. HammerTime will mark this 
future as done when its closing process is complete. Useful to wait for HammerTime to completely close itself.

**property hammertime.HammerTime.closed**

Return True if HammerTime as completely closed itself, False otherwise. This property is read-only.
    
**property hammertime.HammerTime.completed_count**
    
The amount of requests HammerTime has successfully complete. Retries do not count. This property is read-only.
    
**property hammertime.HammerTime.requested_count**
    
The amount of requests HammerTime has sent. Retries do not count. This property is read-only.

**method hammertime.HammerTime.request(\*args, \*\*kwargs)**

Create a request and wrap it in a asyncio.Task, scheduling its execution. Return the task wrapping the request.
All parameters are used to create the [HTTP entry](#entry), see hammertime.http.Entry.create.
    
Return: An asyncio.Task wrapping the request.
    
**method hammertime.HammerTime.successful_requests()**

Return an AsyncIterator with the entries of all successful requests. No exception are raised, and the entry of 
requests that caused an exception are not returned. Entries are returned as soon as they are available, thus the
entries are not in the same order as the requests.
    
Return: An AsyncIterator containing [HTTP entries](#entry) of the successful requests.
    
**coroutine hammertime.HammerTime.close()**

Close HammerTime and set the closed future as done.
    
**method hammertime.HammerTime.set_proxy(proxy)**

Set the proxy used to send the HTTP requests

Parameters: 
* proxy: The URL of the HTTP proxy.


## Stats class

**class hammertime.core.Stats()**

Initialize a new Stats instance with the current time as the start time.

**attribute hammertime.core.Stats.init**

A time object representing the time this stats object was created.

**attribute hammertime.core.Stats.requested**

The amount of requests made by HammerTime, ignoring retries.

**attribute hammertime.core.Stats.completed**

The amount of requests made by HammerTime for which a response, not discarded by heuristics, was received.

**attribute hammertime.core.Stats.retries**

The amount of retries made by HammerTime for all the requests.

**property hammertime.core.Stats.duration**

The elapsed time since the stats instance was initialized.

**property hammertime.core.Stats.rate**

The amount of completed requests divided by the current duration.


## Entry

**function Entry.create(\*args, response=None, arguments=None, \*\*kwargs)**

Creates a new HTTP entry.

Parameters: 
* args: arguments used to create the request.
* response: An instance of the response class.
* arguments: A dictionary used to store optional arguments.
* kwargs: keyword arguments used to create the request.
    
Return a namedtuple representing an HTTP entry containing the following fields:
* request: An instance of the Request class.
* result: An instance of the Result class.
* response: An instance of the StaticResponse class.
* arguments: A dictionary used to store optional arguments with the entry.

**class Request(url, \*, method='GET', headers=None)**

Contains information about the HTTP request.

Parameters: 
* url: A string containing the URL for the request.
* method: the HTTP method for the request. Default is GET.
* headers: A dictionary with custom values for header fields. Default is None (no custom values).
                
**class Result()**

Contains information about the result of the HTTP request, like the attempt count and the read length.
    
**class StaticResponse(code, headers, content=None)**

Contains the response for the request.

Parameters: 
* code: the HTTP status code of the response.
* headers: the HTTP headers of the response.
* content: the content of the response. Use the raw property to get/set the response in raw bytes.


## RetryEngine class

**class hammertime.engine.RetryEngine(engine, \*, loop, stats, retry_count=0)**

The engine used by HammerTime to send requests and handle retries if they fail.

Parameters:
* engine: The AioHttpEngine used to send a HTTP request and apply the heuritics to the request.
* loop: The event loop used by the request engine.
* stats: The [Stats](#stats-class) instance used to store statistics about HammerTime.
* retry_count: The amount of time the retry engine will resend a failed request before dropping it.
                
**coroutine hammertime.engine.RetryEngine.perform(entry, heuristics)**

The coroutine used to send a request for a HTTP entry and handle retries.

Parameters: 
* entry: The [HTTP entry](#entry) for the request.
* heuristics: The heuristics to apply to the request.

Return the entry of the request with the response, or raise a StopRequest if the request failed, or was rejected.
                
**coroutine hammertime.engine.RetryEngine.perform_high_priority(entry, heuristics=None)**

The coroutine used to send a request for a HTTP entry and handle retries without being affected by the limit of 
concurrent requests sent with perform.

Parameters: 
* entry: The HTTP entry for the request.
* heuristics: The heuristics to apply to the request. If none, heuristics used with perform will be used.

Return the entry of the request with the response, raise a StopRequest if the request failed or a RejectRequest if the 
request was rejected.

**coroutine hammertime.engine.RetryEngine.close()**

Close the underlying [AioHttpEngine](#aiohttpengine-class).
    
**method hammertime.engine.RetryEngine.set_proxy(proxy)**

Set the proxy used to send the requests
    
Parameters: 
* proxy: A string containing the URL of the proxy.
    

## AioHttpEngine class

**class hammertime.engine.AioHttpEngine(\*, loop, verify_ssl=True, ca_certificate_file=None, proxy=None, timeout=0.2)**

The engine used to send HTTP requests.

Parameters: 
* loop: The asyncio event loop used to send the requests asynchronously.
* verify_ssl: True if SSL authentication should be done. Setting this to False is not recommended for security reasons.
              Default is True.
* ca_certificate_file: The path of a SSL certificate to load for authentication. Required if using a proxy to connect to
                       HTTPS website without disabling SSL verification.
* proxy: The address of the proxy to use to send requests.
* timeout: The connection timeout for the requests. Default is 0.2 seconds.
                
**coroutine hammertime.engine.AioHttpEngine.perform(entry, heuristics)**

Send a HTTP request and apply heuristics to the request.

Parameters: 
* entry: The [entry](#entry) for the HTTP request.
* heuristics: The heuristics to apply to the entry.

**coroutine hammertime.engine.AioHttpEngine.close()**

Close the underlying aiohttp session.

**method hammertime.engine.AioHttpEngine.set_proxy(proxy)**

Set the proxy to use to send requests

Parameters: 
* proxy: A string containing the URL of the proxy.
