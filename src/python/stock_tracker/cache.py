#adapted from https://stackoverflow.com/a/64816003

#i dont think i need a cache...only ticker.info should be cached, but each request should return updated information, rendering the cache useless

from functools import update_wrapper

class LRU_cache:
	def __init__(self, func, maxsize=128):
		self.cache = collections.OrderedDict()
		self.func = func
		self.maxsize = maxsize
		update_wrapper(self, self.func)

		self.hits = 0
		self.misses = 0

	def __call__(self, *args, **kwargs):
		cache = self.cache
		key = self._generate_hash_key(*args, **kwargs)
		if key in cache:
			self.hits += 1
			cache.move_to_end(key)
			return cache[key]
		self.misses += 1
		result = self.func(*args, **kwargs)
		cache[key] = result
		if len(cache) > self.maxsize:
			cache.popitem(last=False)
		return result

	def __repr__(self):
		return self.func.__repr__()

	def clear_cache(self):
		self.cache.clear()
		self.hits = 0
		self.misses = 0

	def cache_remove(self, *args, **kwargs):
		"""Remove an item from the cache by passing the same args and kwargs"""
		key = self._generate_hash_key(*args, **kwargs)
		if key in self.cache:
			self.cache.pop(key)

	def cache_replace(self, value, *args, **kwargs):
		key = self._generate_hash_key(*args, **kwargs)
		self.cache[key] = value

	@staticmethod
	def _generate_hash_key(*args, **kwargs):
		key = hash(args)+hash(frozenset(sorted(kwargs.items())))
		return key

	def cache_info(self):
		return "maxsize={}, cursize={}, hits={}, misses={}".format(self.maxsize, len(self.cache), self.hits, self.misses)