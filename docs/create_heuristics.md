# How to Add a Custom Heuristic

Heuristics is one of the key concepts in HammerTime, allowing rapid filtering and discarding of responses based on 
response code as they are received, adjusting the timeout for the requests dynamically to adapt to the server speed, or 
patching the headers of requests. If the currently available heuristics do not suit all your needs, it is easy to add 
your own. Just create a class with the following interface:

```python
class MyHeuristic:
    
    def set_engine(self, engine):
        
    def set_kb(self, kb):
    
    async def before_request(self, entry):
    
    async def after_headers(self, entry):
    
    async def after_response(self, entry):
    
    async def on_timeout(self, entry):
    
    async def on_request_successful(self, entry):
    
    async def on_error(self, entry):
        
```

The class for your heuristic must support at least one of the four [events](#events): before_request, after_headers, 
after_response or on_timeout.

set_engine and set_kb are optional. set_engine allows your heuristic to have a reference to the retry engine of 
HammerTime. set_kb allows your heuristic to store its data in the [knowledge base](#knowledge-base).


## Events

A heuristic define methods that are called at a specific moment in a request lifetime. All events take a HammerTime
entry as their argument. Currently, the existing events for a heuristic are:

* before_request: called just before a request is performed. Useful to modify an entry before it is send (e.g. to add 
                  headers to the request).
* after_headers: called just after a response to a request has been received, but before the response body is read. 
                 Useful to discard response based on status code (e.g. discard all 404).
* after_response: called after the content of the response has been read. Useful for filtering based on content.
* on_timeout: called when the request timeout, before the retry is performed. Useful to log timeout in the knowledge 
              base.
* on_request_successful: called after all other events when the request was successful and not rejected by another 
                         heuristic. It is invoked after the entry has released the limiter, so other requests can
                         be scheduled in this event without creating a deadlock.
* on_host_unreachable: called when the host is unreachable, before the engine raises a StopRequest exception.

To create your own heuristic, defined a class with one or more of the events, depending of what your heuristic need 
to do.

Avoid time-consuming operations in heuristics methods, as it can affect the request rate of HammerTime.


## Knowledge base

The knowledge base is an object used by heuristics to store all kind of data about received responses or sent requests, 
allowing dynamic decision making. For example, DynamicTimeout heuristic stores the round-trip time of all requests 
when it receives the response to adjust the timeout dynamically. To use the knowledge base, define a method called 
set_kb in the heuristic. A knowledge base object is passed to this method when the heuristic is added to HammerTime. In
this method, simply assign the object that your heuristic uses to store data as an attribute of the knowledge base:
```python
def set_kb(self, kb):
    kb.status_codes = self.status_codes
```
Assignment to already initialized attribute of the knowledge base will raise an AttributeError.
Objects added to the knowledge base need to be serializable, as the knowledge base can be store to a file to be shared 
between several HammerTime executions.
