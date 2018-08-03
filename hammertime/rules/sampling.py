import hashlib


class ContentHashSampling:

    def __init__(self, hash_method=hashlib.md5):
        self._hash_method = hash_method

    async def after_response(self, entry):
        entry.result.content_hash = self._hash(entry.response)

    def _hash(self, response):
        return self._hash_method(response.raw).digest()
