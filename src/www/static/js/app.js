// var app = angular.module('StockApp', ['infinite-scroll', 'darthwade.loading', 'angularLazyImg']);
// var app = angular.module('StockApp', ['infinite-scroll', 'darthwade.loading']);
var app = angular.module("StockApp", []);

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

// am4core.options.minPolylineStep = 5;
// am4core.options.queue = true;
// am4core.options.onlyShowOnViewport = true;

app.directive("chart", ["$timeout", function($timeout) {
	return {
		restrict: "E",
		scope: {
			"tickerId": "=",
			"chartSuffix": "@",
			"tickerData": "="
		},	//test this with live data
		template: '<canvas id="{{tickerId}}{{chartSuffix}}" style="width: 100%; height: 100%;"></canvas>',
		// template: '<div id="{{tickerId}}{{chartSuffix}}" style="width: 100%; height: 100%;"></div>',
		replace: true,
		link: function($scope) {
			console.log("chart directive:", $scope);

			$scope.$watch("tickerId", function() {
				if ($scope.tickerId) {
					$timeout(function() {
						// console.log(document);
						// var w = new Worker("/js/chart.js");
						// w.postMessage(document);
						// var arr = ArrayBuffer()
						// w.postMessage($scope.tickerData);
						// var chart = am4core.create($scope.tickerId + $scope.chartSuffix, am4charts.XYChart);	//pass this via copy?
						// w.addEventListener("message", function(e) {})

						//test creating using chart.js
						var chartContext = $("#" + $scope.tickerId + $scope.chartSuffix);
						// var chartContext = document.getElementById($scope.tickerId + $scope.chartSuffix).getContext("2d");
						console.log(chartContext);
						var chart = new Chart(chartContext, {
							type: "candlestick",
							data: {
								datasets: [{
									label: "",
									data: $scope.tickerData
								}]
							}
						});

						// var chart = am4core.create($scope.tickerId + $scope.chartSuffix, am4charts.XYChart);
						// // chart.dateFormatter.inputDateFormat = "yyyy-MM-dd";
						// chart.dateFormatter.inputDateFormat = "x";

						// // chart.svgContainer.autoResize = false;

						// // chart.stroke = am4core.color("rgb(215, 218, 220)");
						// chart.fontSize = "0.75rem";
						// chart.fontWeight = 100;
						// chart.paddingLeft = 0;
						// chart.paddingRight = 5;

						// chartWhiteColor = am4core.color("rgb(215, 218, 220)");

						// var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
						// dateAxis.renderer.grid.template.location = 0;
						// dateAxis.skipEmptyPeriods = true;

						// dateAxis.renderer.grid.template.stroke = chartWhiteColor;
						// dateAxis.renderer.labels.template.fill = chartWhiteColor;
						// // dateAxis.renderer.labels.template.disabled = true;

						// chart.paddingBottom = 0;
						// // dateAxis.renderer.labels.template.zIndex = 9999;

						// var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
						// valueAxis.tooltip.disabled = true;

						// valueAxis.renderer.grid.template.stroke = chartWhiteColor;
						// valueAxis.renderer.labels.template.fill = chartWhiteColor;

						// var series = chart.series.push(new am4charts.CandlestickSeries());
						// series.dataFields.dateX = "Date";
						// series.dataFields.valueY = "Close";
						// series.dataFields.openValueY = "Open";
						// series.dataFields.lowValueY = "Low";
						// series.dataFields.highValueY = "High";
						// series.simplifiedProcessing = true;
						// series.tooltipText = "Open: ${openValueY.value}\nLow: ${lowValueY.value}\nHigh: ${highValueY.value}\nClose: ${valueY.value}";
						// // series.tooltip.marginLeft = 0;
						// // series.tooltip.marginRight = 0;
						// // series.tooltip.marginTop = 0;
						// // series.tooltip.marginBottom = 0;

						// chart.cursor = new am4charts.XYCursor();
						// chart.cursor.lineX.stroke = chartWhiteColor;
						// chart.cursor.lineX.strokeOpacity = 1;
						// chart.cursor.lineY.stroke = chartWhiteColor;
						// chart.cursor.lineY.strokeOpacity = 1;
						// chart.cursor.behavior = "panX";
						// chart.cursor.maxPanOut = 0.8;

						// chart.mouseWheelBehavior = "zoomX";
						// chart.zoomOutButton.align = "left";
						// chart.zoomOutButton.icon.disabled = true;
						// chart.zoomOutButton.background.cornerRadius(5, 5, 5, 5);
						// chart.zoomOutButton.background.fill = chartWhiteColor;
						// chart.zoomOutButton.width = 20;
						// chart.zoomOutButton.height = 20;
						// //from: https://www.amcharts.com/docs/v4/tutorials/configuring-the-zoom-out-button/#Custom_image_example
						// var zoomImage = chart.zoomOutButton.createChild(am4core.Image);
						// zoomImage.href = "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiA/PjwhRE9DVFlQRSBzdmcgIFBVQkxJQyAnLS8vVzNDLy9EVEQgU1ZHIDEuMS8vRU4nICAnaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkJz48c3ZnIGVuYWJsZS1iYWNrZ3JvdW5kPSJuZXcgMCAwIDk2IDk2IiBoZWlnaHQ9Ijk2cHgiIGlkPSJ6b29tX291dCIgdmVyc2lvbj0iMS4xIiB2aWV3Qm94PSIwIDAgOTYgOTYiIHdpZHRoPSI5NnB4IiB4bWw6c3BhY2U9InByZXNlcnZlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj48cGF0aCBkPSJNOTAuODI5LDg1LjE3MUw2OC4xMjEsNjIuNDY0QzczLjA0Nyw1Ni4zMDcsNzYsNDguNSw3Niw0MEM3NiwyMC4xMTgsNTkuODgyLDQsNDAsNEMyMC4xMTgsNCw0LDIwLjExOCw0LDQwczE2LjExOCwzNiwzNiwzNiAgYzguNSwwLDE2LjMwNi0yLjk1MywyMi40NjQtNy44NzlsMjIuNzA4LDIyLjcwOGMxLjU2MiwxLjU2Miw0LjA5NSwxLjU2Miw1LjY1NywwQzkyLjM5MSw4OS4yNjcsOTIuMzkxLDg2LjczMyw5MC44MjksODUuMTcxeiAgIE00MCw2OGMtMTUuNDY0LDAtMjgtMTIuNTM2LTI4LTI4czEyLjUzNi0yOCwyOC0yOGMxNS40NjQsMCwyOCwxMi41MzYsMjgsMjhTNTUuNDY0LDY4LDQwLDY4eiIvPjxwYXRoIGQ9Ik01Niw0MGMwLDIuMjA5LTEuNzkxLDQtNCw0SDI4Yy0yLjIwOSwwLTQtMS43OTEtNC00bDAsMGMwLTIuMjA5LDEuNzkxLTQsNC00aDI0QzU0LjIwOSwzNiw1NiwzNy43OTEsNTYsNDBMNTYsNDB6Ii8+PC9zdmc+";
						// zoomImage.width = 10;
						// zoomImage.height = 10;
						// zoomImage.interactionsEnabled = false;
						// zoomImage.paddingLeft = -10;
						// zoomImage.paddingTop = -10;

						// chart.data = $scope.tickerData;

						// $scope.$on("$destroy", function() {
						// 	chart.dispose();
						// });
					}, 0, false);
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
				if ($scope.tickerColor > 0) {
					ele.css({color: "green"});
				}
				else if ($scope.tickerColor < 0) {
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