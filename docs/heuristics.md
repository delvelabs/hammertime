# Getting Started With Heuristics

To use a single heuristic:

```python
from hammertime.rules import RejectStatusCode
from hammertime import HammerTime

hammertime = HammerTime()
reject_5xx = RejectStatusCode(range(500, 600))
hammertime.heuristics.add(reject_5xx)
```

To use more than one heuristic:

```python
from hammertime.rules import RejectStatusCode, DynamicTimeout
from hammertime import HammerTime

hammertime = HammerTime(retry_count=3)
reject_5xx = RejectStatusCode(range(500, 600))
dynamic_timeout = DynamicTimeout(0.01, 2)
heuristics = [reject_5xx, dynamic_timeout]
hammertime.heuristics.add_multiple(heuristics)
```

When multiple heuristics are added to HammerTime, they are called in the order they were added. For example:

```python
heuristic_a = HeuristicA()
heuristic_b = HeuristicB()
hammertime.heuristics.add_multiple([heuristicA, heuristicB])
```

If both heuristic_a and heuristic_b support the same [event](create_heuristics.md#events) (e.g. before_request), then 
the before_request method of heuristic_a will be called before the before_request method of heuristic_b.


## Existing Heuristics

**class hammertime.rules.RejectStatusCode(\*args)**

Used to reject responses based on their HTTP status code.

Parameters:

* args: Iterables containing the status code to reject.

**class hammertime.rules.IgnoreLargeBody(initial_limit=1024\*1024)**
    
Dynamically sets a size limit for the body of HTTP responses and truncates larger body at the calculated limit to 
prevent large response from decreasing performance.
  
Parameters:

* initial_limit: The initial size limit for the response body. Default is 1 MB.

**class hammertime.rules.DynamicTimeout(min_timeout, max_timeout, sample_size=200)**
    
Dynamically adjust the request timeout based on real-time average latency to maximise performance.
  
Parameters:

* min_timeout: Minimum value for the request timeout, in seconds.
* max_timeout: Maximum value for the request timeout, in seconds.
* sample_size: the amount of requests used to calculate the timeout. for example, if the sample size is 100, the last 
               100 requests will be used to calculate the timeout. Default is 200.

**class hammertime.rules.DetectSoft404(distance_threshold=5, match_filter=DEFAULT_FILTER, token_size=4)**
    
Detect and reject response for a page not found when a server does not respond with 404 for pages not found.
  
Parameters:

* distance_threshold: Minimum count of differing bit between two simhash required to consider two simhash to be 
                      different. Default is 5.
* match_filter: Regex to filter characters used to compute the simhash of the responses. Default is 
                r'[\w\u4e00-\u9fcc<>]+'
* token_size: length of the tokens used to compute the simhash of the responses. Default is 4.

The DetectSoft404 heuristic uses its own set of heuristics for the requests it sends (called child heuristics). To 
configure those heuristics:

```python
from hammertime import HammerTime
from hammertime.rules import DetectSoft404, DynamicTimeout
  
hammertime = HammerTime(retry_count=3)
timeout = DynamicTimeout(0.05, 2)
soft_404_detection = DetectSoft404()
soft_404_detection.child_heuristics.add(timeout)
hammertime.heuristics.add_multiple((timeout, soft_404_detection))
```

**class hammertime.rules.SetHeader(name, value)**

Set the value of a field in the HTTP header of the requests.

Parameters:

* name: The name of the field in the HTTP header.
* value: The value for the field.
