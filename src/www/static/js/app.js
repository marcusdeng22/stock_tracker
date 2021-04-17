// var app = angular.module('StockApp', ['infinite-scroll', 'darthwade.loading', 'angularLazyImg']);
// var app = angular.module('StockApp', ['infinite-scroll', 'darthwade.loading']);
var app = angular.module("StockApp", []);

const REFRESH_RATE = 1000;	//1 second refresh for data

//global values for period/intervals: need to display with 3 chars
app.value("periodMap", {
	"1d" : "1d ",
	"5d" : "5d ",
	"2wk": "2wk",
	"1mo": "1mo",
	"3mo": "3mo",
	"6mo": "6mo",
	"1y" : "1y ",
	"2y" : "2y ",
	"5y" : "5y ",
	"10y": "10y",
	"ytd": "ytd",
	"max": "max"
});

app.value("intervalMap", {
	"1m" : "1m ",
	"5m" : "5m ",
	"15m": "15m",
	"30m": "30m",
	"60m": "60m",
	// "90m": "90m",
	// "1h" : "1h ",
	"1d" : "1d ",
	"5d" : "5d ",
	"1wk": "1wk",
	"1mo": "1mo",
	"3mo": "3mo"
});

//these need to have at least a day's interval
app.value("restrictedPeriods", ["3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]);
//these are restricted to a period in days of data
//the values of this map are the DEFAULTS
app.value("restrictedIntervals", {
	// "1m": 7,
	// "5m": 60,
	// "15m": 60,
	// "30m": 60,
	// "60m": 730
	"1m": "1wk",
	"5m": "1mo",
	"15m": "1mo",
	"30m": "1mo",
	"60m": "2y"
});

app.value("allowedIntervalsByPeriods", {
	"1d": ["1m", "5m", "15m", "30m", "60m"],
	"5d": ["1m", "5m", "15m", "30m", "60m"],
	"2wk": ["30m", "15m", "60m", "5m"],
	"1mo": ["30m", "15m", "60m", "5m", "1d"],
	"3mo": ["1d", "5d", "1wk"],
	"6mo": ["1d", "5d", "1wk"],
	"1y": ["1d", "5d", "1wk", "1mo"],
	"2y": ["1d", "5d", "1wk", "1mo"],	//maybe limit to 5d?
	"5y": ["5d", "1wk", "1mo"],			//maybe limit to 1wk?
	"10y": ["1wk", "5d", "1mo", "3mo"],
	"ytd": ["1d", "5d", "1wk", "1mo"],
	"max": ["1wk", "5d", "1mo", "3mo", "1d"]	//allow 1d, but really shouldn't allow it for old stocks
});

app.value("allowedPeriodsByIntervals", {
	"1m": ["5d", "1d"],
	"5m": ["5d", "1d", "2wk", "1mo"],
	"15m": ["2wk", "1mo", "5d", "1d"],
	"30m": ["1mo", "2wk", "5d", "1d"],
	"60m": ["1mo", "2wk", "5d", "1d"],
	"1d": ["1y", "6mo", "3mo", "1mo", "2wk", "2y", "ytd", "max"],	//allow 1d, but really shouldn't
	"5d": ["2y", "1y", "ytd", "max", "6mo", "3mo", "1mo", "2wk"],
	"1wk": ["2y", "1y", "ytd", "max", "6mo", "3mo", "1mo", "2wk"],
	"1mo": ["10y", "2y", "1y", "ytd", "max", "6mo", "3mo", "1mo", "2wk"],
	"3mo": ["10y", "2y", "1y", "ytd", "max", "6mo", "3mo", "1mo", "2wk"]
})

app.directive("repeatLast", ["$timeout", function($timeout) {
	return {
		restrict: "A",
		scope: {
			"repeatLast": "&"	//execute the function
		},
		link: function(scope, ele, attrs) {
			if (scope.$parent.$last) {
				$timeout(function() {
					scope.repeatLast();
				}, 0, false);	//don't trigger another digest cycle
			}
		}
	};
}]);

app.directive("doAfter", ["$timeout", function($timeout) {
	return {
		restrict: "A",
		scope: {
			"doAfter": "&"	//execute the function
		},
		link: function(scope, ele, attrs) {
			console.log(scope);
			$timeout(scope.doAfter, 0, false);	//don't trigger another digest cycle
		}
	};
}]);

// anychart.onDocumentReady(function() {
// 	anychart.theme(anychart.themes.darkTurquoise);
// });

// function isVisible(el) {
// 	var rect = el[0].getBoundingClientRect();

// 	return (
// 		rect.top >= 0 &&
// 		rect.left >= 0 &&
// 		rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && /* or $(window).height() */
// 		rect.right <= (window.innerWidth || document.documentElement.clientWidth) /* or $(window).width() */
// 	);
// }

var observer = new IntersectionObserver(function(entries) {
	entries.forEach((entry) => {
		if (entry.isIntersecting) {
			// console.log(entry.target, "VISIBLE!");
			entry.target.classList.add("live-visible");
		}
		else {
			entry.target.classList.remove("live-visible");
		}
		// console.log(entry, "OBSERVE")
	});
}, {
	// root: $("#homeDiv"),
	// root: document.querySelector("#homeDiv"),
	threshold: 0	//set this to closer to 0 later, 1 for testing
});

const TIMEZONE = new Date().getTimezoneOffset();
const LOCALE = "en-us";
anychart.format.outputTimezone(TIMEZONE);
anychart.format.outputDateTimeFormat("MM/dd h:mm a");
const RED = "#ff3031";
const GREEN = "#00b061";

app.directive("chart", ["$timeout", "$http", "periodMap", "intervalMap", "allowedIntervalsByPeriods", "allowedPeriodsByIntervals",
		function($timeout, $http, periodMap, intervalMap, allowedIntervalsByPeriods, allowedPeriodsByIntervals) {
	const btnSet1 =
		'<div style="float: left;">' +
			'<button class="btn dropdown-toggle btn-secondary small-btn" type="button" data-toggle="dropdown">{{periodMap[selectedPeriod]}}</button>' +
			'<div class="dropdown-menu" style="min-width: 35px;">' +
				'<div class="dropdown-item" ng-repeat="(periodKey, periodVal) in periodMap" ng-click="updatePeriod(periodKey)" style="width: 35px; padding-left: 1px;">{{periodVal}}</div>' +
			'</div>' +
		'</div>';
	const btnSet2 =
		'<button class="btn dropdown-toggle btn-secondary small-btn" type="button" data-toggle="dropdown">{{intervalMap[selectedInterval]}}</button>' +
			'<div class="dropdown-menu" style="min-width: 35px;">' +
				'<div class="dropdown-item" ng-repeat="(intervalKey, intervalVal) in intervalMap" ng-click="updateInterval(intervalKey)" style="width: 35px; padding-left: 1px;">{{intervalVal}}</div>' +
			'</div>' +
		'</div>';
	return {
		restrict: "E",
		scope: {
			// "tickerId": "=",
			// "tickerData": "=",
			"ticker": "=",			//full ticker data
			"chartSuffix": "@",		//suffix for chart canvas
			"controlPosition": "@",	//top or right
			"displayCtrl": "<"		//expression to eval to hide/show
		},
		template:
			'<div style="width: 100%; height: 100%; border: 1px solid rgb(106, 109, 111);">' +
				// '<div ng-if="controlPosition == ' + "'top'" + '" ng-show="displayCtrl" style="position: relative; float: left; width: calc(33vw - 10px); height: 45px;">' +	
				'<div ng-if="controlPosition == ' + "'top'" + '" ng-show="displayCtrl" style="float: left; width: calc(33vw - 10px); height: 45px;">' +					//top button control
					'<div style="margin: 5px 30px;">' +
						btnSet1 +

						'<div style="margin-left: 25px; float: left;">' +
							btnSet2 +
					'</div>' +
				'</div>' +
				// '<div ng-if="controlPosition == ' + "'top'" + '" ng-show="displayCtrl" style="position: relative; float: left; width: calc(33vw - 10px); height: calc(100% - 45px);">' + 	//research canvas wrapper
				'<div ng-if="controlPosition == ' + "'top'" + '" ng-show="displayCtrl" style="float: left; width: calc(33vw - 10px); height: calc(100% - 45px); overflow: hidden;">' + 	//research canvas wrapper
					// '<canvas id="{{ticker.ticker}}{{chartSuffix}}"></canvas>' +
					'<div id="{{ticker.ticker}}{{chartSuffix}}"></div>' +
				'</div>' +
				// '<div ng-if="controlPosition == ' + "'right'" + '" style="position: relative; float: left; width: 540px; height: 171px;">' +
				'<div ng-if="controlPosition == ' + "'right'" + '" style="float: left; width: 540px; height: 171px; overflow: hidden;">' +											//home canvas wrapper
					// '<canvas id="{{ticker.ticker}}{{chartSuffix}}"></canvas>' +
					'<div id="{{ticker.ticker}}{{chartSuffix}}" style="height: 190px;"></div>' +
				'</div>' +
				//vertical center from: https://stackoverflow.com/a/18200048
				// '<div ng-if="controlPosition == ' + "'right'" + '" style="position: relative; float: left; width: 45px; height: 100%; padding: 0px 5px;">' +	
				'<div ng-if="controlPosition == ' + "'right'" + '" style="float: left; width: 45px; height: 100%; padding: 0px 5px; border: 1px solid blue">' +								//right button control
					// '<div style="position: absolute; margin: auto; width: 50%; height: 50%; top: 0px; left: 5px; bottom: 0px;">' +
					'<div style="margin-top: 25px;>' +
						btnSet1 +

						'<div style="margin-top: 25px; float: left;">' +
							btnSet2 +
					'</div>' +
				'</div>' +
			'</div>'
		,
		replace: true,
		link: function($scope) {
			// var chart;
			// var dataTable;

			function buildChart(data) {
				$scope.dataTable = anychart.data.table().addData(data);

				var candleMapping = $scope.dataTable.mapAs({
					open: 1,
					high: 2,
					low: 3,
					close: 4
				});

				var volumeMapping = $scope.dataTable.mapAs({"value": {column: 5, type: "sum"}});

				$scope.chart = anychart.stock();
				var plot = $scope.chart.plot(0);

				var candle = plot.candlestick(candleMapping);
				//color candles
				candle.risingFill(GREEN, 0.5).risingStroke(GREEN, 0.5).fallingFill(RED, 0.5).fallingStroke(RED, 0.5);
				// candle.risingFill("green", 0.5).risingStroke("green", 0.5).fallingFill("red", 0.5).fallingStroke("red", 0.5);

				var candleY = plot.yAxis(0);
				candleY.labels().format("{%value}{decimalsCount:2, zeroFillDecimals: true}");
				candleY.orientation("right");

				var vol = plot.column(volumeMapping);
				//set height and color
				vol.name("v").maxHeight("20%").bottom(0).risingFill(GREEN, 0.5).risingStroke(GREEN, 0.5).fallingFill(RED, 0.5).fallingStroke(RED, 0.5);
				// vol.name("v").maxHeight("20%").bottom(0).risingFill("green", 0.5).risingStroke("green", 0.5).fallingFill("red", 0.5).fallingStroke("red", 0.5);
				//create scale
				var volScale = anychart.scales.linear();
				vol.yScale(volScale);
				//create axis
				var volAxis = plot.yAxis(1);
				volAxis.scale(volScale);
				volAxis.enabled(false);	//disable to hide it; showing currently for debugging

				//plot moving 20 and 50 averages using close
				var movingMapping = $scope.dataTable.mapAs({value: 4})
				plot.ema(movingMapping, 20).series().stroke("1 #0081f2");
				plot.ema(movingMapping, 50).series().stroke("1 #ad6eff");

				//hide legend
				plot.legend(false);

				//hide scroller
				$scope.chart.scroller(false);

				//set crosshair label to exact
				plot.crosshair().enabled(true).xStroke("white").yStroke("white").displayMode("float");//.displayMode("float");
				var candleCross = plot.crosshair().yLabel(0);
				candleCross.axisIndex(0);
				candleCross.format(function() {
					// console.log("candle cross", this);
					return this.rawValue.toFixed(2);
				});
				// candleCross.background({fill: "blue"})

				var volCross = plot.crosshair().yLabel(1, false);
				// var volCross = plot.crosshair().yLabel(1);
				// volCross.axisIndex(1);
				// volCross.enabled(false);

				//set tooltip position; after margin fix
				var tooltip = $scope.chart.tooltip();
				tooltip.positionMode("chart").anchor("left-top").allowLeaveStage(true).offsetX(-120);//.offsetX().offsetY(#);
				//tooltip.displayMode("union");
				// tooltip.displayMode("single");

				//format candle tooltip
				candle.tooltip().format(function() {
					try {
						// console.log("candle tool", this.close)
						return "o: " + this.open.toFixed(2) + "\nh:\t" + this.high.toFixed(2) + "\nl:\t" + this.low.toFixed(2) + "\nc:\t" + this.close.toFixed(2);
					}
					catch (err) {};
				});
				//format volume tooltip
				vol.tooltip().format(function() {
					//convert the volume (this.value) (is int) to 3 digit + K/M/B
					try {
						var ret = this.value.toString();
						const lengthMap = [
							[12, "T"],
							[9, "B"],
							[6, "M"],
							[3, "K"]
						];
						for (const j of lengthMap) {
							var i = j[0];
							if (ret.length > i) {
								return "v:\t" + this.value + " " + (this.value / (1 * 10**i)).toFixed(2) + j[1];
							}
						}
						return "v:\t" + this.value;
					}
					catch (err) {};
				});

				$scope.chart.container($scope.ticker.ticker + $scope.chartSuffix);
				$scope.chart.interactivity().zoomOnMouseWheel(true);

				$scope.chart.grouping().enabled(false);

				//padding on right
				$scope.chart.xScale("scatter");	//not ordinal so gap is viewable
				$scope.chart.xScale().maximumGap({intervalsCount: 1, unitCount: 1, unitType: "year"});

				//format x axis
				var myXAxis = plot.xAxis();
				myXAxis.showHelperLabel(false);
				function formatXLabels() {
					console.log(this);
					var fmt;
					if ($scope.selectedPeriod == "ytd" || $scope.selectedPeriod == "1mo") {
						fmt = "MM/dd"
					}
					else if ($scope.selectedPeriod == "5d") {
						if ($scope.selectedInterval == "1m") {
							fmt = "E h:mm a"
						}
						else {
							fmt = "E"
						}
					}
					else if ($scope.selectedPeriod == "1d") {
						fmt = "h:mm a"
					}
					else {
						fmt = "MM/dd/yy"
					}
					return anychart.format.dateTime(this.value, fmt, TIMEZONE, LOCALE);
				};
				// myXAxis.labels().format(formatXLabels);
				// myXAxis.minorLabels().format(formatXLabels);
				//disable minor x grid?

				//set chart colors
				$scope.chart.background().fill("rgba(26,26,27,1.8)");
				plot.yGrid(true).xGrid(true).xMinorGrid(true);
				plot.xGrid().stroke("#51555c");
				plot.xMinorGrid().stroke("#51555c");
				plot.yGrid().stroke("#51555c");
				// plot.yGrid(true).xGrid(true).yMinorGrid(true).xMinorGrid(true);

				//set margins
				$scope.chart.padding().left(5).top(5).right(60);

				//async ready check
				var stage = $scope.chart.container();
				stage.listenOnce("renderfinish", function() {
					$scope.chart.selectRange(data[0][0], data[data.length-1][0]);
					observer.observe(document.querySelector("#" + $scope.ticker.ticker + $scope.chartSuffix))
					$scope.ready = true;
				});

				//async draw
				$scope.chart.draw(true);
			};

			function createChart(data) {
				if ($scope.chart) {
					//dispose
					console.log("disposing");
					$scope.chart.dispose();
					$scope.ready = false;
					$timeout(function() {
						buildChart(data);
					}, 100);
				}
				else {
					buildChart(data);
				}
			};

			$scope.$watch("ticker.ticker", function() {
				if ($scope.ticker.ticker) {
					// if (chart) {
					// 	console.log("destroying old chart");
					// 	// chart.destroy();
					// 	chart.dispose();
					// }
					$timeout(function() {
						createChart($scope.ticker.data.history);
					});
				}
			}, 0, false);

			// $scope.$watchCollection("ticker.data.history", function(newVal) {
			// 	console.log("ticker data watch hit for", $scope.ticker.ticker, newVal);
			// 	$timeout(function() {	//timeout to wait for chart to be created
			// 		if (newVal && $scope.chart && $scope.ready) {
			// 			console.log("pushing data to:", $scope.ticker.ticker, $scope.chart);

			// 			if ($scope.oldInterval == $scope.selectedInterval) {
			// 				//this is new data but with the same interval, so feed it
			// 				console.log("feeding")
			// 				$scope.dataTable.addData(newVal);
			// 			}
			// 			else {
			// 				//this is new data with a different interval, so we need to recreate the chart
			// 				console.log("building")
			// 				// createChart(newVal);
			// 				$scope.chart.xScale().maximumGap(null);
			// 				$scope.dataTable.remove().addData(newVal);
			// 	$scope.chart.xScale().maximumGap({intervalsCount: 1, unitCount: 1, unitType: "year"});
			// 				$scope.chart.selectRange(newVal[0][0], newVal[newVal.length-1][0]);
			// 				$scope.oldInterval = $scope.selectedInterval;
			// 			}
			// 		}
			// 	});
			// });
		},
		controller: function($scope) {
			$scope.periodMap = periodMap;
			$scope.intervalMap = intervalMap;
			$scope.allowedIntervalsByPeriods = allowedIntervalsByPeriods;
			$scope.allowedPeriodsByIntervals = allowedPeriodsByIntervals;

			//defaults on load
			$scope.selectedPeriod = "1y";
			$scope.selectedInterval = "1d";

			$scope.oldPeriod = $scope.selectedPeriod;
			$scope.oldInterval = $scope.selectedInterval;

			// $scope.clearData = false;	//set this to true if we need to drop data, otherwise we merge new data in with existing

			$scope.ready = false;		//set this to true once we load the chart
			var myTimeout;				//this holds the interval and allows us to cancel it

			//always request live data unless specified
			//we don't update the graph data everytime unless our interval is 1m
			$scope.getData = function(live=true) {
				// //clear the interval
				if (myTimeout) {
					clearInterval(myTimeout);
				}

				//check if we are visible
				if (!($("#" + $scope.ticker.ticker + $scope.chartSuffix).hasClass("live-visible"))) {
					//try again later
					// console.log("trying", $scope.ticker.ticker, "live later")
					myTimeout = setInterval($scope.getData, REFRESH_RATE);
					return;
				}
				//TODO: get data
				//if $scope.clearData then we drop existing and replace it
				//else we merge it
				//start the interval again

				var myRequest;
				var endRequest = false;
				var lastStartIdx;
				if (!live) {
					myRequest = {
						ticker: $scope.ticker.ticker,
						period: $scope.selectedPeriod,
						interval: $scope.selectedInterval,
						live: false
					};
				}
				else {
					myRequest = {
						ticker: $scope.ticker.ticker,
						// period: "1d",						//want only the latest data. since it is live
						interval: $scope.selectedInterval,	//this is not guaranteed to return the selected interval; we need to drop the past element if it's not correct
						live: true
					}
					lastStartIdx = $scope.ticker.data.history.length;
					if (lastStartIdx >= 2) {
						lastStartIdx -= 2;		//want to query second to last to now, since the latest might be out of date
						myRequest["start"] = $scope.ticker.data.history[lastStartIdx][0]	//set start to time
						endRequest = true;
					}
					else {
						myRequest["period"] = $scope.selectedPeriod;	//not enough data, so request the full period
					}
				}

				console.log("POSTING FOR STOCK DATA");
				$http.post("/getStockData", myRequest).then(function(data) {
					//process the data and update the fields
					data = data.data.data[0]	//this is for now; if we need to switch to a queued aggregator post, then we will have to select the data
					console.log("got stock data; LIVE:", live, $scope.ticker, data);
					for (const key of ["change", "changePercent", "lastPrice"]) {
							$scope.ticker.data[key] = data.data[key];
					}
					for (const [k, v] of Object.entries(data.data.fields)) {
						$scope.ticker.data.fields[k] = v;
					}
					//append data if live
					//we need to parse the data and flatten it if it's not the right interval
					if (live && endRequest) {
						//merge received data with old data if we did not query for the full period
						//get the timestamp interval
						// var interval = $scope.ticker.data.history[1].t - $scope.ticker.data.history[0].t;
						console.log($scope.ticker.data)

						$scope.ticker.data.history.splice(lastStartIdx, $scope.ticker.data.history.length - lastStartIdx, ...data.data.history);

						//update the chart data
						$scope.dataTable.addData($scope.ticker.data.history.slice(lastStartIdx));

						// var last = $scope.ticker.data.history.length - 1;
						// if (data.data.history.length == (last + 1)) {					//same length, so the new data will replace the old data
						// 	$scope.ticker.data.history = data.data.history;
						// 	console.log("LIVE same length")
						// }
						// else {
						// 	//merge the last part of result into data
						// 	// merge data from reverse
						// 	var toAdd = [];
						// 	for (var i = data.data.history.length - 1; i >= 0; i--) {
						// 		if (data.data.history[i].t == $scope.ticker.data.history[last].t) {
						// 			console.log("LIVE REPLACE LAST");
						// 			$scope.ticker.data.history.pop();		//remove last item, since we are replacing it
						// 			toAdd.unshift(data.data.history[i]);
						// 			break;
						// 		}
						// 		else if (data.data.history[i].t > $scope.ticker.data.history[last].t) {
						// 			toAdd.unshift(data.data.history[i]);
						// 		}
						// 		else {
						// 			break;
						// 		}
						// 	}
						// 	$scope.ticker.data.history = $scope.ticker.data.history.concat(toAdd);
						// 	console.log("LIVE longer", toAdd)
						// }
					}
					else {
						$scope.ticker.data.history = data.data.history;
						console.log("NOT LIVE");

						//set the entire data range
						//TODO: start a spinner
						$scope.ticker.data.history = data.data.history;
						// $scope.dataTable.addData($scope.ticker.data.history);
						//set the new info
						$scope.chart.xScale().maximumGap(null);
						$scope.dataTable.remove().addData($scope.ticker.data.history);
						$scope.chart.xScale().maximumGap({intervalsCount: 1, unitCount: 1, unitType: "year"});
						$scope.chart.selectRange($scope.ticker.data.history[0][0], $scope.ticker.data.history[$scope.ticker.data.history.length-1][0]);
					}
					// myTimeout = setInterval($scope.getData, REFRESH_RATE);
				}, function(err) {
					console.log("failed to post /getStockData");
					console.log(err);
					$("#ownCtrl").after("<p>ERROR!</p>")
				});
			};

			$scope.updatePeriod = function(key) {
				$scope.oldPeriod = $scope.selectedPeriod;
				$scope.selectedPeriod = key;
				// if ($scope.selectedPeriod in $scope.restrictedPeriods && $scope.selectedInterval in $scope.restrictedIntervals) {
				// 	//our selected period is greater than a month, so we need to switch interval to a day at least
				// 	$scope.selectedInterval = $scope.intervalMap["1d"];
				// 	$scope.clearData = true;
				// }
				if (!($scope.selectedInterval in $scope.allowedIntervalsByPeriods[$scope.selectedPeriod])) {
					$scope.oldInterval = $scope.selectedInterval;
					$scope.selectedInterval = $scope.allowedIntervalsByPeriods[$scope.selectedPeriod][0];
					// console.log("interval not allowed for period; NEW:", $scope.selectedInterval);
					// $scope.clearData = true;
				}

				$scope.getData(false);
			};

			$scope.updateInterval = function(key) {
				$scope.oldInterval = $scope.selectedInterval;
				$scope.selectedInterval = key;
				//TODO: need to include an OR for the current total period (including pan) is greater than allowed for the interval
				// if ($scope.selectedInterval in $scope.restrictedIntervals && ($scope.selectedPeriod in $scope.restrictedPeriods)) {
				// 	//our selected interval is restricted to a certain period, so we reduce our period
				// 	$scope.selectedPeriod = $scope.periodMap["1d"];
				// 	$scope.clearData = true;
				// }
				if (!($scope.selectedPeriod in $scope.allowedPeriodsByIntervals[$scope.selectedInterval])) {
					$scope.oldPeriod = $scope.selectedPeriod;
					$scope.selectedPeriod = $scope.allowedPeriodsByIntervals[$scope.selectedInterval][0];
					// console.log("period not allowed for interval; NEW:", $scope.selectedPeriod);
					// $scope.clearData = true;
				}

				$scope.getData(false);
			};

			//set interval to constantly get new data
			var readyWatch = $scope.$watch("ready", function() {
				if ($scope.ready) {
					console.log("chart ready", $scope.ticker.ticker, $scope.ticker.data.history.length);
					//set interval
					myTimeout = setInterval($scope.getData, REFRESH_RATE);	//every 1 second
					//cancel the watch
					readyWatch();
				}
			});
		}
	};
}]);

app.factory("authIntercept", ["$q", "$window", function($q, $window) {
	var handled = false;
	var responseError = function(err) {
		if (handled) {
			return $q.resolve();
		}
		if (err.status == 403) {
			//set location
			$window.location.href = "/";
			handled = true;
			alert("Session timed out");
			return $q.resolve();
		}
		return $q.reject(err);
	};

	return {
		responseError: responseError
	};
}]);

app.config(["$httpProvider", function($httpProvider) {
	$httpProvider.interceptors.push("authIntercept");
}]);

app.directive("tickerColor", function() {
	return {
		restrict: "A",
		scope: {
			"tickerColor": "="
		},
		link: function ($scope, ele) {
			$scope.$watch("tickerColor", function() {
				var price = parseFloat($scope.tickerColor)
				if (price > 0) {
					ele.css({color: "green"});
				}
				else if (price < 0) {
					ele.css({color: "red"});
				}
				else {
					ele.css({color: "rgb(215, 218, 220)"});
				}
			});
		}
	}
})

app.directive("ngEnter", function() {
	return {
		restrict: "A",
		link: function(scope, element, attrs) {
			var f = function(e) {
				if (e.which === 13) {
					scope.$apply(function() {
						scope.$eval(attrs.ngEnter);
					});
					e.preventDefault();
				}
			}

			element.on("keyup", f);

			scope.$on("$destroy", function() {
				element.off("keyup", f);
			});
		}
	}
});

$(window).on("scroll", function() {
	$(".separator").css({"left": $(this).scrollLeft()});
});

// //https://stackoverflow.com/questions/152975/how-do-i-detect-a-click-outside-an-element
// app.directive("ngOffClose", function() {
// 	return {
// 		restrict: "A",
// 		link: function(scope, element, attrs) {
// 			var f = function(e) {
// 				if ((e.which === 27 || e.which === 1) && !$(e.target).closest(element).length && element.is(":visible")) {
// 					scope.$apply(function() {
// 						scope.$eval(attrs.ngOffClose);
// 					});
// 				}
// 			};

// 			var g = function(e) {
// 				if (e.which === 27 && element.is(":visible")) {
// 					scope.$apply(function() {
// 						scope.$eval(attrs.ngOffClose);
// 					});
// 				}
// 			};

// 			$("body").on("mousedown", f).on("keydown", f);
// 			element.on("keydown", "input", g);

// 			scope.$on("$destroy", function() {
// 				$("body").off("mousedown", f).off("keydown", f);
// 				$(element + " input").off("keydown", "input", g);
// 			});
// 		}
// 	}
// });

// app.factory("youtubeFuncs", ["$http", function($http) {
// 	var data = {};
// 	data.cleanUrl = function(id){
// 		// return /([a-zA-Z0-9_\-]+)/.test(id) && RegExp.lastParen;
// 		ret = id.match(/^.*(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]*).*/);
// 		if (ret != null) {
// 			return ret[1];
// 		}
// 		return
// 	};

// 	data.getThumbnail = function(item) {
// 		// console.log("THUMBNAIL");
// 		// console.log(item);
// 		if (item.url) {
// 			return "https://img.youtube.com/vi/" + data.cleanUrl(item.url) + "/default.jpg";
// 			// return "https://img.youtube.com/vi/" + data.cleanUrl(item.url) + "/0.jpg";
// 		}
// 	}
// 	return data;
// }]);

// app.factory("sortingFuncs", ["orderByFilter", function(orderBy) {
// 	var sortingFuncs = {};
// 	sortingFuncs.sortGlyph = function(reverse, orderVar, type) {
// 		ret = "icon fas fa-chevron-" + (reverse ? "down" : "up");
// 		if (orderVar == "date" && orderVar == type) {
// 			return ret;
// 		}
// 		else if (orderVar == "name" && orderVar == type) {
// 			return ret;
// 		}
// 		else if (orderVar == "relev" && orderVar == type) {
// 			return ret;
// 		}
// 		else {
// 			return "";
// 		}
// 	};

// 	//ordering function: local data only
// 	//TODO: make this a stable sort? https://stackoverflow.com/questions/24678527/is-backbonejs-and-angularjs-sorting-stable
// 	//TODO: deprecate this and use server DB sort
// 	sortingFuncs.sortBy = function(data, reverse, orderVar, propertyName, preserveOrder=false) {
// 		if (!preserveOrder) {
// 			reverse = (propertyName && orderVar === propertyName) ? !reverse : false;
// 		}
// 		orderVar = propertyName;
// 		data = orderBy(data, orderVar, reverse);
// 		return {
// 			"reverse": reverse,
// 			"orderVar": orderVar,
// 			"data": data
// 		}
// 	}
// 	return sortingFuncs;
// }]);

// app.factory("playDatashare", ["$timeout", "$rootScope", function($timeout, $rootScope) {
// 	var data = {};
// 	return data;
// }])

// app.factory("songDatashare", ["$compile", "$timeout", "$http", "$window", "sortingFuncs", "$rootScope", function($compile, $timeout, $http, $window, sortingFuncs, $rootScope) {
// 	var VARIES = "<varies>";
// 	var data = {};
// 	return data;
// }]);