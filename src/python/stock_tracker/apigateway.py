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

absDir = os.getcwd()

DOWNLOAD_FOLDER = "download"

TZ = "US/Central"	#central standard time
CLOSE_TIME = " 15:00:00-06:00"	#CST time

import signal
import concurrent.futures
import yfinance
import numpy
import investpy

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

def estimateNumber(value):
	ret = str(value)
	thresholds = [(12, "T"), (9, "B"), (6, "M"), (3, "K")]
	for i, k in thresholds:
		if len(ret) > i:
			return "{:.3f}{}".format(value / (1 * 10**i), k)
	return ret

def convertToPercent(value, round_to=3):
	#this expects a raw decimal value
	return ("{:0." + str(round_to) + "f}%").format(value)

def computeChange(lastPrice, previousClose):
	diff = lastPrice - previousClose
	per = convertToPercent(diff / lastPrice)
	return float("{:0.3f}".format(diff)), per

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
	#get history
	#don't get dividends and splits, round to 3 decimals
	history = numpy.round(ticker.history(period=period, interval=interval, auto_adjust=True, actions=False), 3)
	#convert to central time if possible
	try:
		if "Date" in history:
			history = history.tz_localize(TZ)
		if "Datetime" in history:
			history = history.tz_convert(TZ)
		history = history.reset_index()
	except:
		print("failed to convert data to", TZ)
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

	#pull info
	info = ticker.info
	myInfo = {}

	for k in ["previousClose", "open", "bid", "bidSize", "ask", "askSize", "dayLow", "dayHigh", "fiftyTwoWeekLow", \
			"fiftyTwoWeekHigh", "volume", "averageVolume", "quoteType", "sector", "totalAssets", "marketCap", "navPrice", \
			"trailingEps", "trailingPE", "yield", "dividendRate", "dividendYield", "exDividendDate", \
			"longName", "sector", "longBusinessSummary"]:
		#fix individual values to rounded strings
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

	if myInfo["bid"] and myInfo["bidSize"]:
		myInfo["bid"] = "{} x {}".format(myInfo["bid"], myInfo["bidSize"])
		del myInfo["bidSize"]
	if myInfo["ask"] and myInfo["askSize"]:
		myInfo["ask"] = "{} x {}".format(myInfo["ask"], myInfo["askSize"])
		del myInfo["askSize"]

	if myInfo["dayLow"] and myInfo["dayHigh"]:
		myInfo["dayRange"] = "{} - {}".format(myInfo["dayLow"], myInfo["dayHigh"])
		del myInfo["dayLow"]
		del myInfo["dayHigh"]
	if myInfo["fiftyTwoWeekLow"] and myInfo["fiftyTwoWeekHigh"]:
		myInfo["yearRange"] = "{} - {}".format(myInfo["fiftyTwoWeekLow"], myInfo["fiftyTwoWeekHigh"])
		del myInfo["fiftyTwoWeekLow"]
		del myInfo["fiftyTwoWeekHigh"]

	if info["beta"] is not None:
		myInfo["beta"] = info["beta"]
	elif info["beta3Year"] is not None:
		myInfo["beta"] = info["beta3Year"]
	else:
		myInfo["beta"] = None

	if myInfo["beta"] is not None:
		myInfo["beta"] = "{:0.3f}".format(myInfo["beta"])
	else:
		myInfo["beta"] = "N/A"

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
		myFields["field13"] = ["Fwd Div & Yield:", myInfo["dividendRate"] + " (" + myInfo["dividendYield"] + ")"]
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
		myRequest, sortOrder, period, interval = m_utils.createGetStockQuery(data)

		# period = "6mo"
		period = "1y"
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

		#setup threads
		threadCount = min([myCount, os.cpu_count() * 2])
		start = time.perf_counter()

		#need to get each ticker's price and compute change (both value and percent)
		#use threads for now since it seems to be more consistent

		with concurrent.futures.ThreadPoolExecutor(max_workers=threadCount) as executor:
			# for t in myTickers:
			# 	print("submitting", t)
			# 	future = executor.submit(self.extractInfo, t["ticker"], period, interval)
			# 	t["data"] = future.result()
			myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
			for t, res in zip(myTickers, executor.map(extractInfo, myTickerArgs)):
				t["data"] = res

		# with concurrent.futures.ProcessPoolExecutor(max_workers=threadCount) as executor:
		# 	print("about to submit:", period, interval)
		# 	myTickerArgs = ({"ticker": x["ticker"], "period": period, "interval": interval} for x in myTickers)
		# 	for t, res in zip(myTickers, executor.map(extractInfo, myTickerArgs)):
		# 		t["data"] = res

		print("done waiting", time.perf_counter() - start)

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

		print("returning")
		return {"data": myTickers, "count": myCount}

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def getStockData(self):
		"""
		Returns stock data based on the ticker. Only gives historical data, not stock info

		Expected input:
		{
			"ticker": [(string)],
			"period": (string) (1d, 3d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max),
			"interval": (string) (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
		}
		Returns:
		{
			"data": [
				{
					"ticker": (string),
					//"info": yfinance.info,	//full info, probably not useful?
					"history": {date: [open, high, low, div, split], ...},
				},
				...
			]
		}
		"""
		if hasattr(cherrypy.request, "json"):
			data = cherrypy.request.json
		else:
			raise cherrypy.HTTPError(400, "No data was given")

		#sanitize
		myRequest, _, period, interval = m_utils.createGetStockQuery(data)

		myTickers = [x["ticker"] for x in myRequest]

		if len(myTickers) == 0:
			return {"data": []}

		#download and transform
		history = numpy.round(yfinance.download(myTickers, period=period, interval=interval, progress=False, \
			group_by="ticker", actions=False), 3)
		try:
			if "Date" in history:
				history = history.tz_localize(TZ)
			if "Datetime" in history:
				history = history.tz_convert(TZ)
			history = history.reset_index()
		except:
			print("failed to convert data to", TZ)
		key = ""
		if "Date" in history:
			# history["Datetime"] = history["Date"].apply(lambda x: str(x.date()) + CLOSE_TIME)
			history["Date"] = history["Date"].apply(lambda x: str(x.date()))		#leave as Datetime? YYYY-MM-DD
			key = "Date"
		elif "Datetime" in history:
			history["Datetime"] = history["Datetime"].apply(lambda x: str(x))		#YYYY-MM-DD HH:MM:SS-06:00, where -06:00 is TZ
			key = "Datetime"

		myData = []
		if len(myTickers) == 1:	#cannot refer to each ticker since no subindex
			myData += {"ticker": myTickers[0], "history": history.to_dict("records")}
		else:
			for ticker in myTickers:
				myT = {"ticker": ticker}
				h = history[[key, ticker]]
				h.columns = h.columns.droplevel()
				myT["history"] = h.rename(columns={"": key}).to_dict("records")
				myData += myT

		return {"data": myData}

	def searchHelper(self, text):
		"""
		Helper method to convert text to correct format
		"""
		lookup = {
			"etfs": "ETF",
			"stocks": "Equity",
			"indices": "Index",
			"funds": "Fund",
			"commodities": "Commodity",
			"currencies": "Currency",
			"crypto": "Crypto",
			"bonds": "Bond",
			"certificates": "Certificate",
			"fxfutures": "Future"
		}
		if text in lookup:
			return lookup[text]
		return text.title()

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

		results = investpy.search.search_quotes(searchTerm, n_results=6)

		ret = []
		for r in results:
			ret.append({
				"exchange": r.exchange,
				"name": r.name,
				"type": self.searchHelper(r.pair_type),
				"ticker": r.symbol
			})

		return {"data": ret}

	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	@authUser
	def checkStock(self):
		"""
		Checks if the specified ticker is in the database, and return its properties if it exists.
		Otherwise, return false. Also returns stock info.

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
		myRequest, _, period, interval = m_utils.createGetStockQuery(data, skipDBCheck=True)
		myRequest = {"ticker": m_utils.checkValidData("ticker", data, str).upper()}

		#find
		myStock = self.stockDB().find(myRequest, {"_id": False})

		if myStock.count() == 0:	#default
			myStock = {
				"ticker": myRequest["ticker"],
				"own": False,
				"star": False,
				"notes": ""
			}
		myStock["data"] = extractInfo({"ticker": myRequest["ticker"], "period": period, "interval": interval})

		return {"data": myStock}