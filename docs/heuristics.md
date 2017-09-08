# How to use a heuristic

To use a single heuristic:

```python
from hammertime.rules import RejectStatusCode
from hammertime import HammerTime

hammertime = HammerTime()
reject_5xx = RejectStatusCode(range(500, 600))
hammertime.heuristics.add(reject_5xx)
```

to use more than one heuristic:

```python
from hammertime.rules import RejectStatusCode, DynamicTimeout
from hammertime import HammerTime

hammertime = HammerTime(retry_count=3)
reject_5xx = RejectStatusCode(range(500, 600))
dynamic_timeout = DynamicTimeout(0.01, 2, 3)
heuristics = [reject_5xx, dynamic_timeout]
hammertime.heuristics.add_multiple(heuristics)
```

## existing heuristics

class hammertime.rules.RejectStatusCode(*args)

  Used to reject responses based on their HTTP status code.
  Parameters: * args: iterables containing the status code to reject.

class hammertime.rules.IgnoreLargeBody(initial_limit=1024*1024)
    
  Dynamically sets a size limit for the body of HTTP responses and truncates larger body at the calculated limit to 
  prevent large response from decreasing performance.
  Parameters: * initial_limit: the initial size limit for the response body. Default is 1 MB.

class hammertime.rules.DynamicTimeout(min_timeout, max_timeout, retries, sample_size=200)
    
  Dynamically adjust the request timeout based on real-time average latency to maximise performance.
  Parameters: * min_timeout: Minimum value for the request timeout, in seconds.
              * max_timeout: Maximum value for the request timeout, in seconds
              * retries: The amount of retries for a failed request

class hammertime.rules.DetectSoft404(distance_threshold=5, match_filter=DEFAULT_FILTER, token_size=4)
    
  Detect and reject response for page not found when a server respond with status code 200 instead of 404.
  Parameters: * distance_threshold: Minimum count of differing bit between two simhash required to consider two 
  simhash to be different. Default is 5.
              * match_filter: Regex to filter characters used to compute the simhash of the responses. Default is 
              r'[\w\u4e00-\u9fcc<>]+'
              * token_size: length of the tokens used to compute the simhash of the responses. Default is 4.

  The DetectSoft404 heuristic uses its own set of heuristics for the requests it sends (called child heuristics). To 
  configure those heuristics:
  ```python
  from hammertime import HammerTime
  from hammertime.rules import DetectSoft404, DynamicTimeout
  
  hammertime = HammerTime(retry_count=3)
  timeout = DynamicTimeout(0.05, 2, 3)
  soft_404_detection = DetectSoft404()
  soft_404_detection.child_heuristics.add(timeout)
  hammertime.heuristics.add_multiple((timeout, soft_404_detection))
  ```
  
  
  

# How to add a heuristic in HammerTime

Heuristics is one of the key concepts in HammerTime, allowing rapid filtering and discarding of responses based on 
response code as they are received, adjusting the timeout for the requests dynamically to adapt to the server speed, or 
patching the headers of requests. If the currently available heuristics do not suit all your needs, it is easy to add 
your own.

## Interface
```python
class MyHeuristic:
    
    def set_engine(self, engine):
        
    def set_kb(self, kb):
    
    def before_request(self, entry):
    
    def after_headers(self, entry):
    
    def after_response(self, entry):
    
    def on_timeout(self, entry):
        
```

## Callbacks

A heuristic define methods that are called at a specific moment or event in a request lifetime. All callbacks take a 
HammerTime entry as their sole argument. Currently, the existing callbacks for a heuristic are:
* before_request: called just before a request is performed. Useful to modify an entry before it is send (e.g. to add 
headers to the request).
* after_headers: called just after a response to a request has been received, but before the response body is read. 
Useful to discard response based on status code (e.g. discard all 404).
* after_response: called after the content of the response has been read. Useful for filtering based on content.
* on_timeout: called when the request timeout, before the retry is performed. Useful to log timeout in the knowledge 
base.

To create your own heuristic, defined a class with one or more of the callbacks, depending of what your heuristic need 
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

## Retry engine

The retry engine used by HammerTime can be passed to a heuristic if it needs to send requests when a request is 
received. Define a method named set_engine in your heuristic.
