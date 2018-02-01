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


**class hammertime.rules.FollowRedirects(\*, max_redirects=15)**

Follow redirects and store all the intermediate [HTTP entries](reference.md#entry) in the result of the initial entry. 
The complete path between the initial request and the final (non-redirect) response can be retrieved from 
entry.result.redirects:
```python
entry = await hammertime.request("http://example.com/")
for entry in entry.result.redirects:
    pass
```

Parameters:

* max_redirects: Maximum redirects the heuristic will follow for a request before rejecting the request. Default is 15.


**class hammertime.rules.DetectBehaviorChange(buffer_size=10, match_threshold=5, match_filter=DEFAULT_FILTER, 
                                              token_size=4)**

This heuristic catches the server's behavior change, such as a WAF starting to block all requests. It compares the 
responses and flag the entries as an error behavior when a lot of identical or very similar responses are received.
To test if a request is an error behavior:
```python
entry = await hammertime.request("http://example.com/")
if entry.result.error_behavior:
    # Response is not the normal behavior.
```

Parameters:

* buffer_size: The amount of requests to store for behavior comparison. Each response will be compared with the last 
               *buffer_size* responses. Default is 10.
* match_threshold: The equality threshold in bit when comparing simhash of responses. Two simhash with *match_threshold*
                   or more bit that differ will be unequal. Default is 5.
* match_filter: Regex to filter characters used to compute the simhash of the responses. Default is 
                r'[\w\u4e00-\u9fcc<>]+'
* token_size: length of the tokens used to compute the simhash of the responses. Default is 4.


**class hammertime.rules.RejectErrorBehavior()**

Reject entries that have the attribute *result.error_behavior* set to True by raising hammertime.behavior.BehaviorError.
 Must be called after a heuristic that set this attribute, like DetectBehaviorChange. Add the other heuristic before 
this one when configuring HammerTime's heuristic.


**class hammertime.rules.DeadHostDetection(threshold=50)**

Raise OfflineHostException if the destination host is or become unresponsive. A host is considered dead if the amount of
 requests that timed out in a row exceed threshold. If the host is declared dead all pending requests raise 
 OfflineHostException. Host unreachable errors count as timeout errors.

Parameter:

* threshold: The amount of timed out requests in a row required to declared the destination host as dead. Default is 50.


**class hammertime.rules.FilterRequestFromURL(\*, allowed_urls=None, forbidden_urls=None)**

Reject requests based on the URL. URL of each request is match against one or more url filter, either from 
*allowed_urls* or *forbidden_urls* (but not both), and a request with an URL that matches a filter in the black list or 
that doesn't match at least one filter in the white list is rejected (a RejectRequest exception is raised). The matching
 rules are as follow:
 1. If the filter has a network location (example.com), and the URL network location is inside the filter's network 
    location (www.example.com), the network locations match.
 2. If the filter has a path (/test), and the URL path is inside the filter's path (/test/index.html), the path match.
 3. If the filter contains both a network location and a path (example.com/test), the URL matches only if 1 and 2 
    returned a match.
 4. Else, it returns a match if 1 or 2 returned a match.

A ValueError is raised if both parameters are either None or not None.

Parameter:

* allowed_urls: A string or a list of string with a network location and/or a path describing the allowed URLs for the 
                requests, or None if the forbidden url list is used instead. Ex: "example.com" will match all URL
                to this domain and its subdomain, "/test" will match all URL with a path beginning with /test, and 
                "example.com/test" will match all URL in this domain and its subdomain only if their paths begin with
                /test.
* forbidden_urls: A string or a list of string with a network location and/or a path describing the forbidden URLs for 
                  the requests, or None if the allowed url list is used instead. Matching rules are the same as the 
                  allowed_urls.
