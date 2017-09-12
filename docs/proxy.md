# Proxy support

## HTTP over proxy
To send HTTP requests over a proxy, pass the address of the proxy to HammerTime:

```python
hammertime = HammerTime(proxy="http://127.0.0.1/:8080")
```

Or use the set_proxy method:

```python
hammertime = HammerTime()
hammertime.set_proxy("http://127.0.0.1/:8080")
 ```

## HTTPS over proxy
To send HTTPS requests over a proxy, pass an instance of an AioHttpEngine to HammerTime, with ssl authentication 
disabled (not recommended) or the CA certificate of the proxy (recommended):

```python
from hammertime.engine.aiohttp import AioHttpEngine
from hammertime.config import custom_event_loop
from hammertime import HammerTime

loop = custom_event_loop()
engine = AioHttpEngine(loop=loop, verify_ssl=False, proxy="http://127.0.0.1/:8080")
# or
engine = AioHttpEngine(loop=loop, ca_certificate_file="path/to/proxy/cert.pem", proxy="http://127.0.0.1/:8080")
hammertime = HammerTime(request_engine=engine)
```
