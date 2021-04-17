from stock_tracker.apigateway import getTicker
import datetime

CLOSE = 15	#3PM CST, 4PM EST
# LAST = datetime.datetime.today().strftime("%Y-%m-%d")

'''
need to clear the ticker info cache when the day closes
'''
def clearCache():
	# today = datetime.datetime.today().strftime("%Y-%m-%d")
	# if today != LAST:
		# LAST = today
	myHour = int(datetime.datetime.today().strftime("%H"))
	if myHour >= CLOSE:
		print("cache manager clearing ticker cache")
		print(getTicker.cache_info())
		# getTicker.clear_cache()

'''
this may be used to automatically update the cache info, but for now it seems expensive to do so
def updateCache():
	pass
'''