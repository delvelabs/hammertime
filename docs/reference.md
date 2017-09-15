# HammerTime Reference


## HammerTime class

**class hammertime.HammerTime(loop=loop, request_engine=request_engine, kb=kb, retry_count=0, proxy=None)**

The core class of HammerTime to make requests

Parameters:

* **loop**: Event loop used by HammerTime. By default, it is uvloop if available, else asyncio event loop is
            used. Except if a custom loop is required, you don't need to pass a loop to HammerTime, as the injector 
            automatically initialize HammerTime with a default loop.
* **request_engine**: The AioHttpEngine used to make the HTTP requests. The injector pass a AioHttpEngine automatically.
                      A custom instance can be provided if the default values are not suitable.
* **kb**: The knowledge base used by the heuristics. The injector creates an empty knowledge base by default.
* **retry_count**: The amount of time HammerTime will send a request after the initial attempt failed. A retry count of 
                   3 means that a single request can be sent up to 4 times (the inital attempt + 3 retries). Default is
                   0 (no retry).
* **proxy**: The HTTP proxy used to send the requests. Must be a string containing the proxy URL. Default is none 
             (no proxy).

**attribute stats**

A [Stats](#stats-class) instance containing the statistics about HammerTime requests (duration, rate, retry count, 
success count, etc.)
    
**attribute heuristics**

A Heuristics instance containing the heuristics used by HammerTime.

**attribute closed**

An asyncio.Future used to wait for the completion of the close process of HammerTime. HammerTime will mark this 
future as done when its closing process is complete. Useful to wait for HammerTime to completely close itself.

**property is_closed**

Return True if HammerTime as completely closed itself, False otherwise. This property is read-only.
    
**property completed_count**
    
The amount of requests HammerTime has successfully complete. Retries do not count. This property is read-only.
    
**property requested_count**
    
The amount of requests HammerTime has sent. Retries do not count. This property is read-only.

**method request(\*args, \*\*kwargs)**

Create a request and wrap it in a asyncio.Task, scheduling its execution. Return the task wrapping the request.

Parameters:

* args: The URL for the request.
* kwargs: Optional keyword arguments used to create the [HTTP entry](#entry) with non-default values for *method*
          or *headers*.
    
Return: An asyncio.Task wrapping the request.

**method successful_requests()**

Return an AsyncIterator with the entries of all successful requests. No exception are raised, and the entry of 
requests that caused an exception are not returned. Entries are returned as soon as they are available, thus the
entries are not in the same order as the requests.

Return: An AsyncIterator containing [HTTP entries](#entry) of the successful requests.

**coroutine close()**

Close HammerTime and set the closed future as done.

**method set_proxy(proxy)**

Set the proxy used to send the HTTP requests

Parameters:

* proxy: The URL of the HTTP proxy.


## Stats class

**class hammertime.core.Stats()**

Initialize a new Stats instance with the current time as the start time.

**attribute init**

A time object representing the time this stats object was created.

**attribute requested**

The amount of requests made by HammerTime, ignoring retries.

**attribute completed**

The amount of requests made by HammerTime for which a response, not discarded by heuristics, was received.

**attribute retries**

The amount of retries made by HammerTime for all the requests.

**property duration**

The elapsed time since the stats instance was initialized.

**property rate**

The amount of completed requests divided by the current duration.


## Entry

An entry contains the following attribute:

* request:  
    * url: URL of the request
    * method: HTTP method of the request ('GET' by default).
    * headers: A dict with the name/value of the fields in the HTTP header.
* result:  
    * attempt: The amount of time this request was sent.
    * read_length: The length (in bytes) of the response body that will be read (default is -1, i.e. unlimited).
* response:  
    * code: The HTTP status code of the response
    * headers = The HTTP headers of the response.
    * content: The content of the response in a string.
    * raw: The content of the response in bytes.
    * truncated: True if the response content was truncated because the length exceed the max read length.
* arguments: A dictionary used to store optional arguments with the entry.

**function hammertime.http.Entry.create(\*args, response=None, arguments=None, \*\*kwargs)**

Creates a new HTTP entry. args and kwargs are used to create the request. Return a namedtuple.
