# How to Add a Custom Heuristic

Heuristics is one of the key concepts in HammerTime, allowing rapid filtering and discarding of responses based on 
response code as they are received, adjusting the timeout for the requests dynamically to adapt to the server speed, or 
patching the headers of requests. If the currently available heuristics do not suit all your needs, it is easy to add 
your own. Just create a class with the following interface:

```python
class MyHeuristic:
    
    def set_engine(self, engine):
        
    def set_kb(self, kb):
    
    def load_kb(self, kb):
    
    def set_child_heuristics(self, heuristics):
    
    async def before_request(self, entry):
    
    async def after_headers(self, entry):
    
    async def after_response(self, entry):
    
    async def on_timeout(self, entry):
    
    async def on_request_successful(self, entry):

    async def on_host_unreachable(self, entry):

```

The class for your heuristic must support at least one of the [events](#events): before_request, after_headers,
after_response, on_timeout, on_request_successful or on_host_unreachable.

set_engine, set_kb, load_kb and set_child_heuristics are optional. set_engine allows your heuristic to have a reference 
to the retry engine of HammerTime. set_kb and load_kb allow your heuristic to store its data in the 
[knowledge base](#knowledge-base) and use existing data from if available. set_child_heuristics allows your heuristic to
 apply heuristics chosen by the user to the requests it makes (see [child heuristics](#child-heuristics)).


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
Assignment to already initialized attribute of the knowledge base will raise an AttributeError. In this case, 
```load_kb``` will be invoked to allow heuristics that perform the same task to share common data. Consider the 
following example:

```python
soft404 = DetectSoft404()
reject_soft404 = RejectSoft404()
dynamic_timeout = DynamicTimeout(1, 5)


hammertime.heuristics.add_multiple([soft404, reject_soft404, dynamic_timeout])
soft404.child_heuristics.add(dynamic_timeout)
```

We want the DetectSoft404 heuristic to use the same dynamic timeout as HammerTime for the requests it makes. To 
achieve this, we had the DynamicTimeout heuristic as a child heuristic of the DetectSoft404 heuristic. Because the data 
of this heuristic was already added in the knowledge base previously, DynamicTimeout.load_kb will be invoked, which use 
the existing data instead of initializing it in the knowledge base:

```python
def load_kb(self, kb):
    self.timeout_manager = kb.timeout_manager
```

Objects added to the knowledge base need to be serializable, as the knowledge base can be store to a file to be shared 
between several HammerTime executions.

## Child heuristics

If an heuristic needs to make requests to gather further data (see [detect soft 404](heuristics.md#existing-heuristics) 
for an example), it may need to apply some heuristics to the requests it makes (e.g rejecting 404s or adjusting the 
timeout dynamically). To use child heuristics in your heuristic:
```python

class MyHeuristic:

    async def before_request(self, entry):
        #doing some stuff involving requests

    def set_child_heuristics(self, heuristics):
        self.child_heuristics = heuristics
        

h = HammerTime()
my_heuristic = MyHeuristic()

h.heuristics.add(my_heuristic)

my_heuristic.child_heuristics.add(DynamicTimeout(1, 5))

```

Check the [section about child heuristics](heuristics.md#child-heuristic) for more details
