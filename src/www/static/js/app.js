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

Chart.Tooltip.positioners.topLeft = function (elements, eventPosition) {
	return {
		x: 0,
		y: 0
	};
};

function customTooltip(tooltipModel) {
	var tooltipEl = document.getElementById("chartjs-tooltip");

	if (!tooltipEl) {
		tooltipEl = document.createElement("div");
		tooltipEl.id = "chartjs-tooltip";
		tooltipEl.innerHTML = "<table></table>";
		document.body.appendChild(tooltipEl);
	}

	if (tooltipModel.opacity === 0) {
		tooltipEl.style.opacity = 0;
		return;
	}
	if (tooltipModel.body) {
		var titleLines = tooltipModel.title || [];
		var bodyLines = tooltipModel.body[0].lines;

		var innerHtml = '<tbody>';

		bodyLines.forEach(function(body) {
			innerHtml += '<tr><td>' + body + '</td></tr>';
		});
		innerHtml += '</tbody>';

		var tableRoot = tooltipEl.querySelector('table');
		tableRoot.innerHTML = innerHtml;
	}

	// `this` will be the overall tooltip
	var position = this._chart.canvas.getBoundingClientRect();

	// Display, position, and set styles for font
	tooltipEl.style.opacity = 1;
	tooltipEl.style.position = 'absolute';
	tooltipEl.style.left = position.left + window.pageXOffset + 'px';
	tooltipEl.style.top = position.top + window.pageYOffset + 'px';
	tooltipEl.style.fontFamily = tooltipModel._bodyFontFamily;
	tooltipEl.style.fontSize = tooltipModel.bodyFontSize + 'px';
	tooltipEl.style.fontStyle = tooltipModel._bodyFontStyle;
	tooltipEl.style.padding = tooltipModel.yPadding + 'px ' + tooltipModel.xPadding + 'px';
	tooltipEl.style.pointerEvents = 'none';
}

app.directive("chart", ["$timeout", function($timeout) {
	return {
		restrict: "E",
		scope: {
			"tickerId": "=",
			"chartSuffix": "@",
			"tickerData": "="
		},	//test this with live data
		// template: '<canvas id="{{tickerId}}{{chartSuffix}}" style="width: 100%; height: 100%;"></canvas>',
		template: '<canvas id="{{tickerId}}{{chartSuffix}}"></canvas>',
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
						// console.log(chartContext);
						// console.log(Chart.defaults.financial);
						var myConfig = {
							type: "candlestick",
							data: {
								datasets: [{
									// labels: "test",
									data: $scope.tickerData,
									// borderWidth: 0,
									// hoverBorderWidth: 0,
									// hoverBorderColor
									borderColor: "white"
								}]
							},
							options: {
								title: {
									display: false
								},
								legend: {
									display: false
								},
								tooltips: {
									enabled: false,
									titleFontSize: 10,
									bodyFontSize: 10,
									custom: customTooltip,
									position: "topLeft",
									displayColors: false
								},
								responsive: true,
								maintainAspectRatio: false,
								plugins: {
									zoom: {
										pan: {
											enabled: true,
											mode: 'x',
											// onPan: function(c) {console.log("panning");}
										},
										zoom: {
											enabled: true,
											mode: 'xy',
											// onZoom: function(c) {console.log("zooming");}
										}
									},
									crosshair: {
										line: {
											width: 1,
											color: "white",
											dashPattern: [10, 10]
										},
										sync: {
											enabled: false
										},
										zoom: {
											enabled: false
										}
									}
								}
							}
						};
						// //merge with the defaults in order to support v13b
						// for (var i in Chart.defaults.financial) {
						// 	if (!(i in myConfig.options)) {
						// 		myConfig.options[i] = Chart.defaults.financial[i];
						// 	}
						// }
						var chart = new Chart(chartContext, myConfig);
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