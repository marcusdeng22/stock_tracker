#!/usr/bin/env python3

from __future__ import unicode_literals

import cherrypy
import os
import threading
import glob
import zipfile
import shutil
import pymongo
import functools
import time

from bson.objectid import ObjectId
from io import BytesIO
from uuid import uuid4

import stock_tracker.utils as m_utils

import datetime
from operator import itemgetter
#import ratelimit	#this causes issues with shutting down the server, replacing with random delay
import random
import pandas

TIME_LIMIT = 0.2	#0.2 second limit
ATTEMPT_LIMIT = 5	#5 attempts before erroring

absDir = os.getcwd()

DOWNLOAD_FOLDER = "download"

TZ = "US/Central"	#central standard time
CLOSE_TIME = " 15:00:00-06:00"	#CST time

import signal
import concurrent.futures
# import yfinance
import numpy
import yahooquery
import investpy

NO_VAL = "N/A"

exit = threading.Event()
def quit(signo, _frame):
	print("Interrupt caught, shutting down")
	exit.set()
	cherrypy.engine.exit()

for sig in ("TERM", "HUP", "INT"):
	signal.signal(getattr(signal, "SIG" + sig), quit)

def authUser(func):
	'''
	Verify user is logged in; redirect if not
	'''
	@functools.wraps(func)
	def decorated_function(*args, **kwargs):
		user = cherrypy.session.get('name', None)

		# no user means force a login
		if user is None:
			raise cherrypy.HTTPError(403, "Not logged in")
		return func(*args, **kwargs)

	return decorated_function

'''
@functools.lru_cache(maxsize=128)
def getTicker(tickerId):
	try:
		ticker = yfinance.Ticker(ticker)
	except:
		print("ticker", ticker, "does not exist")
		return {}		#error!
	errCount = 0
	ret = {}
	while errCount < 5:
		try:
			ret = {
				"tickerObj": ticker,
				"info": ticker.info
			}
			#sleep here?
			break
		except:
			print("error getting ticker {} info".format(tickerId))
			errCount += 1

	return ret
'''

def estimateNumber(value):
	ret = str(value)
	thresholds = [(12, "T"), (9, "B"), (6, "M"), (3, "K")]
	for i, k in thresholds:
		if len(ret) > i:
			return "{:.3f}{}".format(value / (1 * 10**i), k)
	return ret

def convertToPercent(value, round_to=3):
	#this expects a raw decimal value
	return ("{:+0." + str(round_to) + "f}%").format(value)

def convertToSigned(value):
	return "{:+0.3f}".format(value)

def computeChange(lastPrice, previousClose):
	diff = lastPrice - previousClose
	per = convertToPercent(diff / lastPrice * 100)
	return "{:0.3f}".format(diff), per

# @ratelimit.sleep_and_retry
# @ratelimit.limits(calls=1, period=TIME_LIMIT)
'''
def extractHistory(ticker, period="1y", start=None, end=None, interval="1d", attempt=1):
	if attempt >= ATTEMPT_LIMIT:
		print("FAILED TO RETREIVE {} HISTORY AFTER {} ATTEMPTS".format(ticker, ATTEMPT_LIMIT))
		return [], 0	#error!

	try:
		if isinstance(ticker, str):
			ticker= yfinance.Ticker(ticker)
		elif isinstance(ticker, yfinance.ticker.Ticker):
			pass
		else:
			raise Exception("invalid ticker object type")
	except:
		print("ticker", ticker, "does not exist")
		return [], 0	#error!

	#get history
	#don't get dividends and splits, round to 3 decimals
	try:
		history = ticker.history(period=period, interval=interval, auto_adjust=True, actions=False)
	except:
		print("FAILED TO RETREIVE {} HISTORY; ATTEMPT {} of {}".format(ticker.ticker, attempt, ATTEMPT_LIMIT))
		time.sleep(random.uniform(0.01, 0.2))	#add a small random delay
		return extractHistory(ticker, period, start, end, interval, attempt+1)

	# history["avg20"] = history["Close"].rolling(20).mean()

	history = numpy.round(history, 3)
	history = history.reset_index()
	if "Date" in history:
		# history["Date"] = history["Date"].astype(numpy.int64) // 10**6
		history["Date"] = history["Date"].apply(lambda x: str(x))
	if "Datetime" in history:
		# history["Datetime"] = history["Datetime"].astype(numpy.int64) // 10**6
		history["Datetime"] = history["Datetime"].dt.tz_localize(None).apply(lambda x: str(x))

	lastPrice = history["Close"].tail(1).item()

	history.fillna("", inplace=True)

	history.columns = ["t", "o", "h", "l", "c", "v"]
	# history.columns = ["t", "o", "h", "l", "c", "v", "avg20"]

	#convert to format for library to parse
	# history = history.to_dict("records")
	history = history.values.tolist()

	return history, lastPrice
'''

def extractHistory(ticker, period="1y", start=None, end=None, interval="1d"):
	#flatten start date and extract the start period; do the same for end
	startDate = startTime = endDate = endTime = None
	if start:
		startDate = start.date()
		startTime = start.time()
	if end:
		endDate = end.date()
		endTime = end.time() 
	history = ticker.history(period=period, interval=interval, start=startDate, end=endDate, adj_ohlc=True)
	if isinstance(history, dict):
		print("HISTORY IS DICT")
		print(ticker, period, start, end, interval)
		print(history)
	# try:
	if isinstance(history.index.get_level_values(1)[0], pandas.Timestamp):
		# print("index is timestamp")
		history = history.loc[(slice(None), slice(start, end)), :]
	else:
		# print("index is date")
		history = history.loc[(slice(None), slice(startDate, endDate)), :]
	# except:
	# 	print("ERROR SLICING")
	# 	print(history)
	#process: fill NaN to 0 and round to 3 decimals
	history.fillna(0, inplace=True)
	history = numpy.round(history, 3)
	#reset date index and convert date
	history = history.reset_index("date")
	history["date"] = history["date"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))
	# history["date"] = history["date"].apply(lambda x: str(x))
	#columns are: date, open, low, high, close, volume, dividends, but not guaranteed in order, and dividends may not be present (this is ok)
	#order columns
	col = ["date", "open", "high", "low", "close", "volume"]
	if "dividends" in history:
		col.append("dividends")
		# history = history.astype({"dividends": float}, copy=True)
	history = history[col]
	# history = history.astype({x: float for x in ["open", "high", "low", "close"]}, copy=True)
	# history = history.astype({"volume": int}, copy=True)
	#extract per ticker
	ret = {}
	for t in ticker.symbols:
		# ret[t] = history.loc[t].values.tolist()
		temp = history.loc[t].values
		if temp.ndim == 1:
			print("temp:", type(temp), temp)
			# temp = numpy.ndarray((2,), buffer=temp)
			# temp = numpy.asarray([temp])
			temp = [str(temp[0]), *[float(x) for x in temp[1:]]]
			temp[5] = int(temp[5])
			ret[t] = [temp]
		else:
			ret[t] = temp.tolist()
		#fix for conversion?
		# if len(ret[t]) == 1:
		# 	ret[t] = [ret[t]]
		# if len(ticker.symbols) == 1:
		# 	print("copy ret:", temp.size, temp.ndim, list([x, type(x)] for x in temp.tolist()))
	# if len(ret) == 1:
	# 	print("extract ret:", ret, type(temp), list([x, type(x)] for x in ret[ticker.symbols[0]][0]))
	return ret
"""
# @ratelimit.sleep_and_retry
# @ratelimit.limits()
def getInfo(ticker, attempt=1):
	if attempt >= ATTEMPT_LIMIT:
		print("FAILED TO RETRIEVE {} INFO AFTER {} ATTEMPTS".format(ticker.ticker, ATTEMPT_LIMIT))
		return
	try:
		return ticker.info
	except:
		print("FAILED TO RETRIEVE {} INFO; ATTEMPT {} of {}".format(ticker.ticker, attempt, ATTEMPT_LIMIT))
		time.sleep(random.uniform(0.01, 0.2))	#add a small random delay
		return getInfo(ticker, attempt+1)

def infoLoop(info, keys):
	myInfo = {}
	#fix individual values to rounded strings
	for k in keys:
		if k not in info:
			myInfo[k] = "N/A"
			print(k, "not in info")
			continue
		v = info[k]
		if k in ("marketCap", "totalAssets",):
			if v is not None:
				v = estimateNumber(v)
		elif k == "yield":
			if v is not None:
				v = convertToPercent(v * 100)
		elif k == "dividendRate":
			if v is not None:
				v = "{:0.3f}".format(v)
		elif k == "dividendYield":
			if v is not None:
				v = convertToPercent(v * 100, 2)
		elif k == "exDividendDate":
			if v is not None:
				v = str(datetime.datetime.fromtimestamp(v).date() + datetime.timedelta(days=1))	#fix off by one error
		elif k == "trailingEps":
			if v is not None:
				v = "{:0.3f}".format(v)
		elif k in ("volume", "averageVolume",):
			if v is not None:
				v = "{:,}".format(v)

		myInfo[k] = v

	if "bid" in myInfo and "bidSize" in myInfo and myInfo["bid"] is not None and myInfo["bidSize"] is not None:
		myInfo["bid"] = "{} x {}".format(myInfo["bid"], myInfo["bidSize"])
		del myInfo["bidSize"]
	else:
		myInfo["bid"] = "N/A"
	if "ask" in myInfo and "askSize" in myInfo and myInfo["ask"] is not None and myInfo["askSize"] is not None:
		myInfo["ask"] = "{} x {}".format(myInfo["ask"], myInfo["askSize"])
		del myInfo["askSize"]
	else:
		myInfo["ask"] = "N/A"

	if "dayLow" in myInfo and "dayHigh" in myInfo and myInfo["dayLow"] is not None and myInfo["dayHigh"] is not None:
		myInfo["dayRange"] = "{} - {}".format(myInfo["dayLow"], myInfo["dayHigh"])
	else:
		myInfo["dayRange"] = "N/A"
	if "fiftyTwoWeekLow" in myInfo and "fiftyTwoWeekHigh" in myInfo and myInfo["fiftyTwoWeekLow"] is not None and myInfo["fiftyTwoWeekHigh"] is not None:
		myInfo["yearRange"] = "{} - {}".format(myInfo["fiftyTwoWeekLow"], myInfo["fiftyTwoWeekHigh"])
	else:
		myInfo["yearRange"] = "N/A"

	if "beta" in info and info["beta"] is not None:
		myInfo["beta"] = info["beta"]
	elif "beta3Year" in info and info["beta3Year"] is not None:
		myInfo["beta"] = info["beta3Year"]
	else:
		myInfo["beta"] = None

	if myInfo["beta"] is not None:
		myInfo["beta"] = "{:0.3f}".format(myInfo["beta"])
	else:
		myInfo["beta"] = "N/A"

	if "dividendRate" in myInfo and "dividendYield" in myInfo and myInfo["dividendRate"] is not None and myInfo["dividendRate"] != "N/A":
		print(myInfo["longName"], myInfo["dividendRate"], myInfo["dividendYield"])
		myInfo["dividendQuote"] = myInfo["dividendRate"] + " (" + myInfo["dividendYield"] + ")"
	else:
		myInfo["dividendQuote"] = "N/A"

	return myInfo

def quickExtractInfo(kwargs):
	#guaranteed to be in data
	ticker = kwargs["ticker"]
	period = kwargs["period"]
	# start = kwargs["start"]
	# end = kwargs["end"]
	interval = kwargs["interval"]

	doInfo = kwargs["doInfo"] if "skipInfo" in kwargs else True

	try:
		ticker = yfinance.Ticker(ticker)
	except:
		print("ticker", ticker, "does not exist")
		return {}		#error!

	history, lastPrice = extractHistory(ticker, period=period, interval=interval)

	#get info
	if doInfo:
		try:
			info = getInfo(ticker)
		except:
			return {}	#error!

		myInfo = infoLoop(info, ["previousClose", "bid", "bidSize", "ask", "askSize", "dayLow", "dayHigh", "volume", "averageVolume"])

		myFields = {
			"field0": ["Previous Close:", myInfo["previousClose"]],
			"field2": ["Bid:", myInfo["bid"]],
			"field3": ["Ask:", myInfo["ask"]],
			"field4": ["Day's Range:", myInfo["dayRange"]],
			"field6": ["Volume:", myInfo["volume"]],
			"field7": ["Avg. Volume:", myInfo["averageVolume"]],
		}
		#compute the change from the latest record
		change, changePercent = computeChange(lastPrice, myInfo["previousClose"])

		return {
			"history": history,
			"fields": myFields,
			"change": change,
			"changePercent": changePercent,
			"lastPrice": "{:0.3f}".format(lastPrice)
		}
	else:
		return {
			"history": history,
			"lastPrice": "{:0.3f}".format(lastPrice)
		}

def extractInfo(kwargs):
	ticker = kwargs["ticker"]
	period = kwargs["period"]
	interval = kwargs["interval"]
	print("extractInfo", ticker, period, interval)
	try:
		ticker = yfinance.Ticker(ticker)
	except:
		print("ticker", ticker, "does not exist")
		return {}		#error!
	'''
	#get history
	#don't get dividends and splits, round to 3 decimals
	history = numpy.round(ticker.history(period=period, interval=interval, auto_adjust=True, actions=False), 3)
	#convert to central time if possible
	# try:
	# 	if "Date" in history:
	# 		history = history.tz_localize(TZ)
	# 	if "Datetime" in history:
	# 		history = history.tz_convert(TZ)
	# 	history = history.reset_index()
	# except:
	# 	print("failed to convert data to", TZ)
	history = history.reset_index()
	if "Date" in history:
		# history["Datetime"] = history["Date"].apply(lambda x: str(x.date()) + CLOSE_TIME)
		# history["Date"] = history["Date"].apply(lambda x: str(x.date()))		#leave as Datetime? YYYY-MM-DD
		history["Date"] = history["Date"].astype(numpy.int64) // 10**6
	if "Datetime" in history:
		# history["Datetime"] = history["Datetime"].apply(lambda x: str(x))		#YYYY-MM-DD HH:MM:SS-06:00, where -06:00 is TZ
		history["Datetime"] = history["Datetime"].astype(numpy.int64) // 10**6

	lastPrice = history["Close"].tail(1).item()

	history.fillna(0, inplace=True)

	print(history.columns)
	#test col renaming for chart.js
	history.columns = ["t", "o", "h", "l", "c", "v"]

	#convert to format for d3 to parse
	history = history.to_dict("records")
	'''

	history, lastPrice = extractHistory(ticker, period=period, interval=interval)
	print("got history {}".format(ticker.ticker))

	#pull info
	try:
		info = getInfo(ticker)
		print("got info {}".format(ticker.ticker))
	except:
		return {}	#error!
	myInfo = infoLoop(info, ["previousClose", "open", "bid", "bidSize", "ask", "askSize", "dayLow", "dayHigh", "fiftyTwoWeekLow", \
			"fiftyTwoWeekHigh", "volume", "averageVolume", "quoteType", "sector", "totalAssets", "marketCap", "navPrice", \
			"trailingEps", "trailingPE", "yield", "dividendRate", "dividendYield", "exDividendDate", \
			"longName", "sector", "longBusinessSummary"])

	#handle individual types
	infoETF = ["YTD Daily Total Return", "Expense Ratio (net)", "Inception Date"]
	infoEQUITY = ["Earnings Date"]
	i = 0
	if myInfo["quoteType"] == "ETF":
		my_institutional_holders = ticker.institutional_holders
		if not my_institutional_holders.empty:
			for j in infoETF:
				myInfo[j] = my_institutional_holders[1][my_institutional_holders[0] == j].item()
		else:
			for j in infoETF:
				myInfo[j] = "N/A"
	elif myInfo["quoteType"] == "EQUITY":
		my_calendar = ticker.calendar
		if not my_calendar.empty:
			for j in infoEQUITY:
				myInfo[j] = my_calendar.loc[j].map(lambda x: str(x.date())).to_list()
				if j == "Earnings Date":
					print("CONVERTING:", myInfo[j])
					#convert to a string
					if len(myInfo[j]) == 1:
						myInfo[j] = myInfo[j][0]
					else:
						myInfo[j] = str(myInfo[j][0]) + " - " + str(myInfo[j][-1])
		else:
			for j in infoEQUITY:
				myInfo[j] = "N/A"

	#extract relevant fields
	myFields = {
		"name": myInfo["longName"],
		"sector": myInfo["sector"],
		"summary": myInfo["longBusinessSummary"],
		"field0": ["Previous Close:", myInfo["previousClose"]],
		"field1": ["Open:", myInfo["open"]],
		"field2": ["Bid:", myInfo["bid"]],
		"field3": ["Ask:", myInfo["ask"]],
		"field4": ["Day's Range:", myInfo["dayRange"]],
		"field5": ["52 Week Range:", myInfo["yearRange"]],
		"field6": ["Volume:", myInfo["volume"]],
		"field7": ["Avg. Volume:", myInfo["averageVolume"]],
	}
	if myInfo["quoteType"] == "ETF":
		myFields["field8"] = ["Net Assets:", myInfo["totalAssets"]]
		myFields["field9"] = ["NAV:", myInfo["navPrice"]]
		myFields["field10"] = ["PE Ratio (TTM):", myInfo["trailingPE"]]
		myFields["field11"] = ["Yield:", myInfo["yield"]]
		myFields["field12"] = ["YTD Daily Total Return:", myInfo["YTD Daily Total Return"]]
		myFields["field13"] = ["Beta (5Y Monthly):", myInfo["beta"]]
		myFields["field14"] = ["Expense Ratio (net):", myInfo["Expense Ratio (net)"]]
		myFields["field15"] = ["Inception Date:", myInfo["Inception Date"]]

		myFields["quoteType"] = "ETF"
	elif myInfo["quoteType"] == "EQUITY":
		myFields["field8"] = ["Market Cap:", myInfo["marketCap"]]
		myFields["field9"] = ["Beta (5Y Monthly):", myInfo["beta"]]
		myFields["field10"] = ["PE Ratio (TTM):", myInfo["trailingPE"]]
		myFields["field11"] = ["EPS (TTM):", myInfo["trailingEps"]]
		myFields["field12"] = ["Earnings Date:", myInfo["Earnings Date"]]
		myFields["field13"] = ["Fwd Div & Yield:", myInfo["dividendQuote"]]
		myFields["field14"] = ["Ex-Dividend Date:", myInfo["exDividendDate"]]
		myFields["field15"] = ["", ""]

		myFields["quoteType"] = "Equity"
	
	#compute the change from the latest record
	change, changePercent = computeChange(lastPrice, myInfo["previousClose"])

	#construct and return
	return {
		"history": history,
		# "info": myInfo,
		"fields": myFields,
		"change": change,
		"changePercent": changePercent,
		"lastPrice": "{:0.3f}".format(lastPrice)
	}
"""
#pass format_key=None if chaining to extract internal dictionaries
def extract(key, data, format_key="fmt"):
	if not isinstance(data, dict):
		return NO_VAL
	ret = NO_VAL
	if key in data:
		if format_key is not None and isinstance(data[key], dict):
			if format_key in data[key]:
				ret = data[key][format_key]
			elif "fmt" in data[key]:
				ret = data[key]["fmt"]
		else:
			ret = data[key]
	if isinstance(ret, dict) and len(ret) == 0:
		ret = NO_VAL
	return ret

def extractSharedFields(innerFields, info):
	innerFields["field0"] = ["Previous Close:", extract("previousClose", info["summaryDetail"])]
	innerFields["field1"] = ["Open:", extract("open", info["summaryDetail"])]
	bid = extract("bid", info["summaryDetail"])
	bidSize = extract("bidSize", info["summaryDetail"], format_key="raw")
	ask = extract("bid", info["summaryDetail"])
	askSize = extract("askSize", info["summaryDetail"], format_key="raw")
	if bid != NO_VAL and bidSize != NO_VAL:
		bid = "{} x {}".format(bid, bidSize)
	else:
		bid = NO_VAL
	if ask != NO_VAL and askSize != NO_VAL:
		ask = "{} x {}".format(ask, askSize)
	else:
		ask = NO_VAL
	innerFields["field2"] = ["Bid:", bid]
	innerFields["field3"] = ["Ask:", ask]
	dayLow = extract("dayLow", info["summaryDetail"])
	dayHigh = extract("dayHigh", info["summaryDetail"])
	yearLow = extract("fiftyTwoWeekLow", info["summaryDetail"])
	yearHigh = extract("fiftyTwoWeekHigh", info["summaryDetail"])
	if dayLow != NO_VAL and dayHigh != NO_VAL:
		dayRange = "{} - {}".format(dayLow, dayHigh)
	else:
		dayRange = NO_VAL
	if yearLow != NO_VAL and yearHigh != NO_VAL:
		yearRange = "{} - {}".format(yearLow, yearHigh)
	else:
		yearRange = NO_VAL
	innerFields["field4"] = ["Day's Range:", dayRange]
	innerFields["field5"] = ["52 Week Range:", yearRange]
	innerFields["field6"] = ["Volume:", extract("volume", info["summaryDetail"], format_key="longFmt")]
	innerFields["field7"] = ["Avg. Volume:", extract("averageVolume", info["summaryDetail"], format_key="longFmt")]

def extractInfo(ticker, live=False):
	if live:
		modules = ["price", "summaryDetail"]
	else:
		modules = ["price", "summaryProfile", "summaryDetail", "fundProfile", "defaultKeyStatistics", "calendarEvents", "financialData"]
	info = ticker.get_modules(modules)
	#process each module per ticker
	ret = {}
	for tickerName, t in info.items():
		# if live:	#this is for a single module only; DEPRECATED
		# 	ret[tickerName] = {
		# 		"changePercent": extract("regularMarketChangePercent", t),
		# 		"change": extract("regularMarkChange", t),						#does this need to be raw?
		# 		"lastPrice": extract("regularMarketPrice", t)
		# 	}
		# 	continue
		#price; common for live or full info
		inner = {
			# "changePercent": convertToPercent(extract("regularMarketChangePercent", t["price"]) * 100),
			"changePercent": extract("regularMarketChangePercent", t["price"]),
			"change": convertToSigned(extract("regularMarketChange", t["price"], format_key="raw")),						#does this need to be raw?
			"lastPrice": extract("regularMarketPrice", t["price"]),					#does this need to be raw?
			"fields": {}
		}
		quoteType = extract("quoteType", t["price"])
		#fields 0-7 for ETF or Equity quotes
		if quoteType in ["ETF", "EQUITY"]:
			extractSharedFields(inner["fields"], t)
		else:
			#TODO: handle for other quote types
			ret[tickerName] = inner
			continue
		if live:
			ret[tickerName] = inner
			continue
		#remainder fields
		inner["fields"]["name"] = extract("longName", t["price"])
		inner["fields"]["sector"] = extract("sector", t["summaryProfile"])
		inner["fields"]["summary"] = extract("longBusinessSummary", t["summaryProfile"])
		inner["fields"]["quoteType"] = quoteType
		#switch on the quoteType
		if quoteType == "ETF":
			# extractSharedFields(inner["fields"], t)
			#handle fields 8-15
			inner["fields"]["field8"] = ["Net Assets:", extract("totalAssets", t["summaryDetail"])]
			inner["fields"]["field9"] = ["NAV:", extract("navPrice", t["summaryDetail"])]
			inner["fields"]["field10"] = ["PE Ratio (TTM):", extract("trailingPE", t["summaryDetail"])]
			inner["fields"]["field11"] = ["Yield:", extract("yield", t["summaryDetail"])]
			inner["fields"]["field12"] = ["YTD Daily Total Return:", extract("ytdReturn", t["defaultKeyStatistics"])]
			beta = extract("beta", t["defaultKeyStatistics"])
			if beta == NO_VAL:
				beta = extract("beta3Year", t["defaultKeyStatistics"])
			inner["fields"]["field13"] = ["Beta (5Y Monthly):", beta]
			inner["fields"]["field14"] = ["Expense Ratio (net):", extract("annualReportExpenseRatio", extract("feesExpensesInvestment", t["fundProfile"], format_key=None))]
			inner["fields"]["field15"] = ["Inception Date:", extract("fundInceptionDate", t["defaultKeyStatistics"])]
		elif quoteType == "EQUITY":
			inner["fields"]["quoteType"] = "Equity"
			# extractSharedFields(inner["fields"], t)
			#handle fields 8-15
			inner["fields"]["field8"] = ["Market Cap:", extract("marketCap", t["summaryDetail"])]
			beta = extract("beta", t["defaultKeyStatistics"])
			if beta == NO_VAL:
				beta = extract("beta3Year", t["defaultKeyStatistics"])
			inner["fields"]["field9"] = ["Beta (5Y Monthly):", beta]
			inner["fields"]["field10"] = ["PE Ratio (TTM):", extract("trailingPE", t["summaryDetail"])]
			inner["fields"]["field11"] = ["EPS (TTM):", extract("trailingEps", t["defaultKeyStatistics"])]
			earningsRange = extract("earningsDate", extract("earningsDate", t["calendarEvents"], format_key=None), format_key=None)
			if earningsRange != NO_VAL and isinstance(earningsRange, list):
				if len(earningsRange) > 1:
					earningsRange = "{} - {}".format(earningsRange[0]["fmt"], earningsRange[-1]["fmt"])
				else:
					earningsRange = "{}".format(earningsRange[0]["fmt"])
			else:
				earningsRange = NO_VAL
			inner["fields"]["field12"] = ["Earnings Date:", earningsRange]
			dividendRate = extract("dividendRate", t["summaryDetail"])
			dividendYield = extract("dividendYield", t["summaryDetail"])
			if dividendRate != NO_VAL and dividendYield != NO_VAL:
				dividendQuote = "{} ({})".format(dividendRate, dividendYield)
			else:
				dividendQuote = NO_VAL
			inner["fields"]["field13"] = ["Fwd Div & Yield:", dividendQuote]
			inner["fields"]["field14"] = ["Ex-Dividend Date:", extract("exDividendDate", t["summaryDetail"])]
			inner["fields"]["field15"] = ["1y Target Est:", extract("targetMeanPrice", t["financialData"])]
		elif quoteType == "MUTUALFUND":
			inner["fields"]["quoteType"] = "Mutual Fund"
			#TODO: fill fields

		ret[tickerName] = inner
	return ret

def getQuoteInfo(dataStore, live=False, period="1y", start=None, end=None, interval="1d"):
	#build ticker object
	ticker = yahooquery.Ticker([i["ticker"] for i in dataStore], formatted=True, asynchronous=True)
	# print("created ticker obj:", list(ticker.symbols), "base:", [i["ticker"] for i in dataStore])
	# print("test info:", ticker.get_modules(["price", "summaryDetail"]))
	#get info and history
	myInfo = extractInfo(ticker, live=live)
	# print(myInfo)
	myHist = extractHistory(ticker, period=period, interval=interval, start=start, end=end)

	#merge info and history into dataStore (is a list)
	for i in dataStore:
		tickerName = i["ticker"]
		# print(myHist[tickerName])
		# print(myInfo[tickerName])
		i["data"] = {
			"history": myHist[tickerName],
			**(myInfo[tickerName])
		}

class ApiGateway(object):

	def __init__(self):
		client = pymongo.MongoClient()
		self.db = client['stock']
		self.colUsers = self.db['users']

	@authUser
	def getUser(self):
		return cherrypy.session.get("name")

	@authUser
	def stockDB(self):
		return self.db[self.getUser() + "-stocks"]

	#DB for exploration?

	# API Functions go below. DO EXPOSE THESE

	@cherrypy.expose
	@cherrypy.tools.json_in()
	def doLogin(self):
		"""
		Logs the user into the system

		Expected input:

			{
				"username": (string),
				"password": (string)
			}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		for k in ["username", "password"]:
			m_utils.checkValidData(k, data, str)
		user = self.colUsers.find_one({"username": data["username"]})
		if user is not None and m_utils.verifyUser(user, data["password"]):
			#set the session name
			cherrypy.session["name"] = data["username"]
			return
		else:
			raise cherrypy.HTTPError(403, "Invalid login credentials")

	@cherrypy.expose
	@cherrypy.tools.json_in()
	def changePassword(self):
		"""
		Changes the password for a user

		Expected input:

			{
				"username": (string),
				"old": (string),
				"new": (string)
			}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		for k in ["username", "old", "new"]:
			m_utils.checkValidData(k, data, str)
		user = self.colUsers.find_one({"username": data["username"]})
		if user is not None:
			newHash, newSalt = m_utils.changePassword(user, data["old"], data["new"])
			self.colUsers.update_one({"username": data["username"]}, {"$set": {"hash": newHash, "salt": newSalt}})
			return
		else:
			raise cherrypy.HTTPError(403, "Invalid login credentials")

	@cherrypy.expose
	@authUser
	def logout(self):
		"""
		Logs user out of system
		"""
		print("LOGGING OUT");
		cherrypy.lib.sessions.expire()

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@authUser
	def addStock(self):
		"""
		Add a song to the database

		Expected input:

			{
				"ticker": (string),
				"own": (bool),
				"star": (bool),
				"notes": (string)
			}
		"""
		# check that we actually have json
		if hasattr(cherrypy.request, 'json'):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, 'No data was given')

		# sanitize the input
		myRequest = m_utils.createStockQuery(data)
		myRequest["indb"] = True

		#insert
		self.stockDB().update_one({"ticker": myRequest["ticker"]}, {"$set": myRequest}, upsert=True)

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@authUser
	def updateStock(self):
		"""
		Updates a stored ticker

		Expected input:
			{
				"ticker": (string),
				"own": (bool) (optional),
				"star": (bool) (optional),
				"notes": (bool) (optional)
			}

		Return: None
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		myRequest = m_utils.createStockQuery(data, ownOpt=True, starOpt=True, notesOpt=True, tickerCreate=False)
		#push update
		try:
			self.stockDB().update_one({"ticker": myRequest["ticker"]}, {"$set": myRequest})
		except:
			raise cherrypy.HTTPError(400, "Ticker not found")

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@authUser
	def removeStock(self):
		'''
		Removes a ticker from the database, if present

		Expected input:
		{
			"ticker": (str)
		}

		Returns none
		'''
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		myRequest = m_utils.checkValidData("ticker", data, str)

		try:
			self.stockDB().delete_one({"ticker": myRequest})
		except:
			raise cherrypy.HTTPError(400, "Failed to delete ticker")

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def getStock(self):
		"""
		Returns stock based on query from the DB. We need to query this at the market open.

		Expected input:
			{
				"ticker": [(string)] (optional),
				"own": (bool) (optional),
				"star": (bool) (optional),
				"notes": [(str)] (optional),
				"sort": ("ticker-asc", "ticker-desc", "price-asc", "price-desc", "change-asc", 
					"change-desc", "change-per-asc", "change-per-desc") (default: ticker-asc),
				"period": (string) (1d, 3d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max) (default: 1y),
				"interval": (string) (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo) (default: 1d)
			}
		Returns:
			{
				"data": [
					{
						"ticker": (string),
						"own": (bool),
						"notes": (string),
						"data": {
							"history": [{date, open, high, low, div, split}, ...],
							"info": {								#below is outdated, and returned in fields
								"previousClose": (double),
								"open": (double),
								"bid": (double),					#combine bid and size?
								"bidSize": (int),
								"ask": (double),					#combine ask and size?
								"askSize": (int),
								"dayLow": (double),					#combine the low and high?
								"dayHigh": (double),
								"fiftyTwoWeekLow": (double),
								"fiftyTwoWeekHigh": (double),
								"volume": (int),
								"averageVolume": (int),
								"quoteType": "ETF" or "EQUITY",
								"sector": (str) or None,			#None if ETF
								"totalAssets": (int) or None,		#None if EQUITY
								"marketCap": (int) or None,			#None if ETF
								"navPrice": (double) or None,		#None if EQUITY; NAV = price per share
								"trailingEps": (double) or None,	#None if ETF; EPS = earnings per share
								"trailingPE": (double) or None,		#None if ETF; PE = price earnings ratio
								"yield": (double) or None,			#None if EQUITY
								"dividendRate": (double) or None,	#None if ETF
								"dividendYield": (double) or None,	#None if ETF
								"exDividendDate": (int) or None,	#None if ETF, int is for UNIX epoch
								"YTD Daily Total Return": (str) or None,	#None if EQUITY
								"Expense Ratio (net)": (str) or None,		#None if EQUITY
								"beta": (double),					#selecting from either 'beta' or 'beta3Year'
								"Expense Ratio (net)": (str) or None,		#None if EQUITY
								"fundInceptionDate": (int) or None,	#None if EQUITY
								"Earnings Date": (str)				#None if ETF
							},
							"fields": {"field0": [...], ...},
							"change": (double),
							"changePercent": (str),
							"lastPrice": (double)
						}
					},
					...
				],
				"count": (int)
			}
		If error for a ticker, then the data is: {"ticker": (string), "own": (bool), "notes": (string), "data": {}}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		# myRequest, sortOrder, period, interval, myTickerObj, _ = m_utils.createGetStockQuery(data, tickerOpt=True, ownOpt=True, starOpt=True, notesOpt=True)
		myRequest, sortOrder, dateInfo, myTickerObj, _ = m_utils.createGetStockQuery(data, tickerOpt=True, ownOpt=True, starOpt=True, notesOpt=True)

		# period = "6mo"
		# period = "1y"
		# interval = "1d"

		#query and return
		myStocks = self.stockDB().find(myRequest, {"_id": False})

		ordered = True
		if sortOrder == "ticker-asc":
			myTickers = list(myStocks.sort("ticker", pymongo.ASCENDING))
		elif sortOrder == "ticker-desc":
			myTickers = list(myStocks.sort("ticker", pymongo.DESCENDING))
		else:
			ordered = False
			myTickers = list(myStocks)

		myCount = len(myTickers)

		if myCount == 0:
			return {"data": myTickers, "count": 0}

		# print("getting quote info")
		# getQuoteInfo(myTickers, period=period, interval=interval)
		getQuoteInfo(myTickers, **dateInfo)

		# #setup threads
		# threadCount = min([myCount, os.cpu_count() * 2])
		# start = time.perf_counter()

		# #need to get each ticker's price and compute change (both value and percent)
		# #use threads for now since it seems to be more consistent

		# with concurrent.futures.ThreadPoolExecutor(max_workers=threadCount) as executor:
		# 	# for t in myTickers:
		# 	# 	print("submitting", t)
		# 	# 	future = executor.submit(self.extractInfo, t["ticker"], period, interval)
		# 	# 	t["data"] = future.result()
		# 	myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
		# 	for t, res in zip(myTickers, executor.map(extractInfo, myTickerArgs)):
		# 		t["data"] = res

		# # with concurrent.futures.ProcessPoolExecutor(max_workers=threadCount) as executor:
		# # 	print("about to submit:", period, interval)
		# # 	myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
		# # 	for t, res in zip(myTickers, executor.map(extractInfo, myTickerArgs)):
		# # 		t["data"] = res

		# print("done waiting", time.perf_counter() - start)

		#sort if not already sorted
		if not ordered:
			sortDict = {
				"price-asc": ("lastPrice", False),
				"price-desc": ("lastPrice", True),
				"change-asc": ("change", False),
				"change-desc": ("change", True),
				"change-per-asc": ("changePercent", False),
				"change-per-desc": ("changePercent", True)
			}
			sortInfo = sortDict[sortOrder]
			myTickers = sorted(myTickers, key=itemgetter(sortInfo[0]), reverse=sortInfo[1])

		# print("returning")
		return {"data": myTickers, "count": myCount}

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def getStockData(self):
		"""
		Returns stock data based on the ticker. Only gives data that may change during the day instead of the full fields

		Expected input:
		{
			"ticker": [(string)],
			"period": (string) (1d, 3d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max) (optional if start given),
			"start": (string) (YYYY-MM-DD) (optional if period given),
			"end": (string) (YYYY-MM-DD) (optional),
			"interval": (string) (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
		}
		Returns:
		# {
		# 	"data": [
		# 		{
		# 			"ticker": (string),
		# 			//"info": yfinance.info,	//full info, probably not useful?
		# 			"fields": {"field0": [...], ...},	//not full info
		# 			"history": {date: [open, high, low, div, split], ...},
		# 		},
		# 		...
		# 	]
		# }
		{
			"history": ...,
			"fields": ...,
			"change": ...,
			"changePercent": ...,
			"lastPrice": ...
		}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		# myTicker, _, period, interval, myTickerObj, myTickerList = m_utils.createGetStockQuery(data, ownOpt=True, starOpt=True, notesOpt=True, tickerCreate=True, skipDBCheck=True)
		myTicker, _, dateInfo, myTickerObj, myTickerList = m_utils.createGetStockQuery(data, ownOpt=True, starOpt=True, notesOpt=True, tickerCreate=True, skipDBCheck=True)

		# myRequest = {
		# 	"ticker": myTicker,
		# 	"period": period,
		# 	"interval": interval
		# }
		# ret = quickExtractInfo(myRequest)

		# ret = {
		# 	"data": [{"ticker": t} for t in myTickerList]
		# }
		# print("getStockData ret:", ret)
		myStock = [{"ticker": t} for t in myTickerList]
		# getQuoteInfo(myStock, period=period, interval=interval)
		getQuoteInfo(myStock, **dateInfo)
		# print(myStock)

		# print(list([x, type(x)] for x in myStock[0]["data"]["history"]))

		# del myStock[0]["data"]["history"]
		try:
			return {
				"data": myStock
			}
		except:
			print("exception!")
			return

		# myTickers = [x["ticker"] for x in myRequest]

		# myCount = len(myTickers)
		# if myCount == 0:
		# 	return {"data": []}

		# #setup threads
		# threadCount = min([myCount, os.cpu_count() * 2])
		# start = time.perf_counter()

		# #need to get each ticker's price and compute change (both value and percent)
		# #use threads for now since it seems to be more consistent

		# with concurrent.futures.ThreadPoolExecutor(max_workers=threadCount) as executor:
		# 	# for t in myTickers:
		# 	# 	print("submitting", t)
		# 	# 	future = executor.submit(self.extractInfo, t["ticker"], period, interval)
		# 	# 	t["data"] = future.result()
		# 	# myTickerArgs = ({"ticker": x["ticker"], "start": start, "end": end, "period": period, "interval": interval} for x in myTickers)
		# 	myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
		# 	for t, res in zip(myTickers, executor.map(quickExtractInfo, myTickerArgs)):
		# 		t["data"] = res

		# # with concurrent.futures.ProcessPoolExecutor(max_workers=threadCount) as executor:
		# # 	print("about to submit:", period, interval)
		# # 	myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
		# # 	for t, res in zip(myTickers, executor.map(extractInfo, myTickerArgs)):
		# # 		t["data"] = res

		# print("done waiting", time.perf_counter() - start)

		# return {"data": myTickers}


		# #download and transform
		# history = numpy.round(yfinance.download(myTickers, period=period, interval=interval, progress=False, \
		# 	group_by="ticker", actions=False), 3)
		# # try:
		# # 	if "Date" in history:
		# # 		history = history.tz_localize(TZ)
		# # 	if "Datetime" in history:
		# # 		history = history.tz_convert(TZ)
		# # 	history = history.reset_index()
		# # except:
		# # 	print("failed to convert data to", TZ)
		# history = history.reset_index()
		# key = ""
		# if "Date" in history:
		# 	# history["Datetime"] = history["Date"].apply(lambda x: str(x.date()) + CLOSE_TIME)
		# 	history["Date"] = history["Date"].apply(lambda x: str(x.date()))		#leave as Datetime? YYYY-MM-DD
		# 	key = "Date"
		# elif "Datetime" in history:
		# 	history["Datetime"] = history["Datetime"].apply(lambda x: str(x))		#YYYY-MM-DD HH:MM:SS-06:00, where -06:00 is TZ
		# 	key = "Datetime"

		# myData = []
		# if len(myTickers) == 1:	#cannot refer to each ticker since no subindex
		# 	myData += {"ticker": myTickers[0], "history": history.to_dict("records")}
		# else:
		# 	for ticker in myTickers:
		# 		myT = {"ticker": ticker}
		# 		h = history[[key, ticker]]
		# 		h.columns = h.columns.droplevel()
		# 		myT["history"] = h.rename(columns={"": key}).to_dict("records")
		# 		myData += myT

		# return {"data": myData}

	# def searchHelper(self, text):
	# 	"""
	# 	Helper method to convert text to correct format
	# 	"""
	# 	lookup = {
	# 		"etfs": "ETF",
	# 		"stocks": "Equity",
	# 		"indices": "Index",
	# 		"funds": "Fund",
	# 		"commodities": "Commodity",
	# 		"currencies": "Currency",
	# 		"crypto": "Crypto",
	# 		"bonds": "Bond",
	# 		"certificates": "Certificate",
	# 		"fxfutures": "Future"
	# 	}
	# 	if text in lookup:
	# 		return lookup[text]
	# 	return text.title()

	def searchHelper(self, key, data, key2=None):
		"""
		helper method to extract info from search results
		"""
		# print(key, data)
		if key in data:
			return data[key]
		if key2 in data:
			return data[key2]
		return NO_VAL

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def searchText(self):
		"""
		Searches for tickers based on provided text; text can be a partial ticker or stock name

		Expected input:
		{
			"data": (str)
		}
		Returns:
		{
			"data": [
				{
					"exchange": (str),
					"name": (str),
					"type": (str) (stocks => Equity, etfs => ETF, else Capitalized),
					"ticker": (str)
				},
				...
			]
		}

		Will only return up to 6 results

		TODO: extend to search within types?
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		searchTerm = m_utils.checkValidData("data", data, str)
		firstTerm = m_utils.checkValidData("first", data, bool, optional=True, default=False)

		print("searching for {}, first: {}".format(searchTerm, firstTerm))

		# results = investpy.search.search_quotes(searchTerm, n_results=6)

		# ret = []
		# for r in results:
		# 	ret.append({
		# 		"exchange": r.exchange,
		# 		"name": r.name,
		# 		"type": self.searchHelper(r.pair_type),
		# 		"ticker": r.symbol
		# 	})

		try:
			results = yahooquery.search(searchTerm, quotes_count=6, news_count=0, first_quote=firstTerm)
		except:
			#failed to query yahoo
			if firstTerm:
				#attempt to return ticker data for text term
				try:
					return {"data": self.checkStockHelper({"ticker": searchTerm}, searchTerm)}
				except:
					raise cherrypy.HTTPError(400, "Yahoo search down, invalid ticker")
			else:
				raise cherrypy.HTTPError(400, "Yahoo search down")
		# print("search results:", results)
		if firstTerm:
			#grab the data for the ticker and return that
			ticker = self.searchHelper("symbol", results)
			if ticker == NO_VAL:
				raise cherrypy.HTTPError(400, "Invalid ticker")
			pass
			myStock = self.checkStockHelper({"ticker": ticker}, ticker)
			return {"data": myStock}
		else:
			ret = []
			for r in results["quotes"]:
				ret.append({
					"exchange": self.searchHelper("exchange", r),
					"name": self.searchHelper("longname", r, "shortname"),
					"type": self.searchHelper("typeDisp", r, "quoteType"),
					"ticker": self.searchHelper("symbol", r)
				})

			return {"data": ret}

	def checkStockHelper(self, myRequest, ticker, period="1y", interval="1d"):
		myStock = list(self.stockDB().find(myRequest, {"_id": False}))
		if len(myStock) == 0:	#default
			print("check stock default")
			myStock.append({
				"ticker": ticker,
				"own": False,
				"star": False,
				"indb": False,
				"notes": ""
			})
		else:
			print("check stock exist")
			myStock = [myStock[0]]	#only return first entry
		# myStock["data"] = extractInfo({"ticker": myRequest["ticker"], "period": period, "interval": interval})

		getQuoteInfo(myStock, period=period, interval=interval)
		return myStock

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def checkStock(self):
		"""
		Checks if the specified ticker is in the database, and return its properties if it exists.
		Otherwise, return false for the database fields. Also returns stock info.

		Expected input:
		{
			"ticker": (str),
			"period": (str) (optional),
			"interval": (str) (optional)
		}

		Returns:
		{
			"ticker": (str),
			"own": (bool),
			"star": (bool),
			"indb": (bool),
			"notes": (str),
			"data": {
				"history": [{date, open, high, low, div, split}, ...],
				"fields": [...],
				"change": (double),
				"changePercent": (str),
				"lastPrice": (double)
			}
		}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		# myRequest, _, period, interval, myTickerObj, myTickerList = m_utils.createGetStockQuery(data, ownOpt=True, starOpt=True, notesOpt=True, skipDBCheck=True)
		myRequest, _, dateInfo, myTickerObj, myTickerList = m_utils.createGetStockQuery(data, ownOpt=True, starOpt=True, notesOpt=True, skipDBCheck=True)
		# print("check stock myRequest:", myRequest)
		# myRequest = {"ticker": myRequest}

		#find
		# myStock = list(self.stockDB().find(myRequest, {"_id": False}))

		myStock = self.checkStockHelper(myRequest, myTickerList[0])		#don't need to specify dateInfo because this is only used for searching

		# if myStock.count() == 0:	#default
		# 	myStock = [{
		# 		"ticker": myTickerList[0],
		# 		"own": False,
		# 		"star": False,
		# 		"indb": False,
		# 		"notes": ""
		# 	}]
		# else:
		# 	myStock = [list(myStock)[0]]	#only return first entry
		# # myStock["data"] = extractInfo({"ticker": myRequest["ticker"], "period": period, "interval": interval})

		# getQuoteInfo(myStock, period=period, interval=interval)
		# # print(myStock)

		return {"data": myStock}