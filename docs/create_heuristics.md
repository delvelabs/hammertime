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
        
```

The class for your heuristic must support at least one of the four [events](#events): before_request, after_headers, 
after_response or on_timeout.

set_engine and set_kb are optional. set_engine allows your heuristic to have a reference to the retry engine of 
HammerTime. set_kb allows your heuristic to store its data in the [knowledge base](#knowledge-base).


## Events

A heuristic define methods that are called at a specific moment in a request lifetime. All callbacks take a HammerTime
entry as their argument. Currently, the existing events for a heuristic are:

* before_request: called just before a request is performed. Useful to modify an entry before it is send (e.g. to add 
                  headers to the request).
* after_headers: called just after a response to a request has been received, but before the response body is read. 
                 Useful to discard response based on status code (e.g. discard all 404).
* after_response: called after the content of the response has been read. Useful for filtering based on content.
* on_timeout: called when the request timeout, before the retry is performed. Useful to log timeout in the knowledge 
              base.

To create your own heuristic, defined a class with one or more of the events, depending of what your heuristic need 
to do.

Avoid time-consuming operations in heuristics methods, as it can affect the request rate of HammerTime.


## Knowledge base

Heuristics sometimes need a way to collect data about received responses or sent requests and store it to act upon it 
for future requests. The knowledge base allows heuristics to store an object containing data where they can store all 
the data they collect. If your heuristic needs to use the knowledge base, define a method called set_kb in the 
heuristic. A knowledge base object is passed to this method when the heuristic is added to HammerTime, and you add your 
object where you store your data to it. Ex: 
```python
def set_kb(self, kb):
    kb.status_codes = self.status_codes
```
Objects added to the knowledge base need to be serializable, as the knowledge base can be store to a file to be shared 
between several HammerTime executions.
