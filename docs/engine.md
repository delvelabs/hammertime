## RetryEngine class

**class hammertime.engine.RetryEngine(engine, \*, loop, stats, retry_count=0)**

The engine used by HammerTime to send requests and handle retries if they fail.

Parameters:
* engine: The AioHttpEngine used to send a HTTP request and apply the heuritics to the request.
* loop: The event loop used by the request engine.
* stats: The Stats instance used to store statistics about HammerTime.
* retry_count: The amount of time the retry engine will resend a failed request before dropping it.
                
**coroutine perform(entry, heuristics)**

The coroutine used to send a request for a HTTP entry and handle retries.

Parameters: 
* entry: The HTTP entry for the request.
* heuristics: The heuristics to apply to the request.

Return the entry of the request with the response, or raise a StopRequest if the request failed, or was rejected.
                
**coroutine perform_high_priority(entry, heuristics=None)**

The coroutine used to send a request for a HTTP entry and handle retries without being affected by the limit of 
concurrent requests sent with perform.

Parameters:
* entry: The HTTP entry for the request.
* heuristics: The heuristics to apply to the request. If none, heuristics used with perform will be used.

Return the entry of the request with the response, raise a StopRequest if the request failed or a RejectRequest if the 
request was rejected.

**coroutine close()**

Close the underlying AioHttpEngine.
    
**method set_proxy(proxy)**

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
* entry: The entry for the HTTP request.
* heuristics: The heuristics to apply to the entry.

**coroutine hammertime.engine.AioHttpEngine.close()**

Close the underlying aiohttp session.

**method hammertime.engine.AioHttpEngine.set_proxy(proxy)**

Set the proxy to use to send requests

Parameters: 
* proxy: A string containing the URL of the proxy.
