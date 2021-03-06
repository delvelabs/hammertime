## RetryEngine class

**class hammertime.engine.RetryEngine(engine, \*, loop, stats, retry_count=0)**

The engine used by HammerTime to send requests and handle retries if they fail.

Parameters:

* engine: The AioHttpEngine used to send a HTTP request and apply the [heuritics](heuristics.md) to the request.
* loop: The event loop used by the request engine.
* stats: The [Stats](reference.md#stats-class) instance used to store statistics about HammerTime.
* retry_count: The amount of time the retry engine will resend a failed request before dropping it.
                
**coroutine perform(entry, heuristics)**

The coroutine used to send a request for a HTTP entry and handle retries.

Parameters:

* entry: The [HTTP entry](reference.md#entry) for the request.
* heuristics: The [heuristics](heuristics.md) to apply to the request.

Return: The [entry](reference.md#entry) of the request with the response, or raise a StopRequest if the request failed 
or was rejected.
                
**coroutine perform_high_priority(entry, heuristics=None)**

The coroutine used to send a request for a HTTP entry and handle retries without being affected by the limit of 
concurrent requests sent with perform.

Parameters:

* entry: The [HTTP entry](reference.md#entry) for the request.
* heuristics: The [heuristics](heuristics.md) to apply to the request. If none, heuristics used with perform will be 
              used.

Return: The [entry](reference.md#entry) of the request with the response, raise a StopRequest if the request failed or a
 RejectRequest if the request was rejected.

**coroutine close()**

Close the underlying AioHttpEngine.
    
**method set_proxy(proxy)**

Set the proxy used to send the requests
    
Parameters:

* proxy: A string containing the URL of the [proxy](proxy.md).
    

## AioHttpEngine class

**class hammertime.engine.AioHttpEngine(\*, loop, verify_ssl=True, ca_certificate_file=None, proxy=None, timeout=0.2, 
disable_cookies=False, client_session=None)**

The engine used to send HTTP requests.

Parameters:

* loop: The asyncio event loop used to send the requests asynchronously.
* verify_ssl: True if SSL authentication should be done. Setting this to False is not recommended for security reasons.
              Default is True.
* ca_certificate_file: The path of a SSL certificate to load for authentication. Required if using a proxy to connect to
                       HTTPS website without disabling SSL verification.
* proxy: The address of the [proxy](proxy.md) to use to send requests.
* timeout: The connection timeout for the requests. Default is 0.2 seconds.
* disable_cookies: If True, the aiohttp.ClientSession won't manage session cookies. False by default.
* client_session: The aiohttp.ClientSession used by the engine if custom settings are required. If None, the engine will
 create one. Default is None.
                
**coroutine hammertime.engine.AioHttpEngine.perform(entry, heuristics)**

Send a HTTP request and apply heuristics to the request. Redirects are not followed, the 3xx response is returned. To
follow redirects, use the [FollowRedirects](heuristics.md) heuristic.

Parameters:

* entry: The [entry](reference.md#entry) for the HTTP request.
* heuristics: The heuristics to apply to the entry.

Return: The [entry](reference.md#entry) of the request with the response, or raise a StopRequest if the request failed 
or was rejected.

**coroutine hammertime.engine.AioHttpEngine.close()**

Close the underlying aiohttp session.

**method hammertime.engine.AioHttpEngine.set_proxy(proxy)**

Set the proxy to use to send requests

Parameters:

* proxy: A string containing the URL of the [proxy](proxy.md).
