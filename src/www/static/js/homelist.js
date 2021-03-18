// app.controller('homelistCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$window', '$http', '$compile',
// 	function($scope, $rootScope, $timeout, $location, $window, $http, $compile) {
app.controller('homelistCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$window', '$http',
	function($scope, $rootScope, $timeout, $location, $window, $http) {		

	$scope.tickerData = [];

	function getTickerData(query={}) {
		console.log("querying ticker data")
		$http.post("/getStock", query).then(function(resp) {
			console.log("/getStock success");
			console.log(resp.data);
			$scope.tickerData = resp.data;
		}, function(err) {
			console.log("failed to post /getStock");
			console.log(err);
			alert("Failed to get ticker data");
		});
	};

	//need to wait for am4 to become ready before fetching data and displaying
	// am4core.ready(function() {
		getTickerData();	//initial loadin of data; TODO: surround this with loading spinner!
		// am4core.useTheme(am4themes_animated);
	// });

	$scope.liveData = function() {
		//get live data every minute (or less?)
	};

	//test color settings
	// setTimeout(function() {
	// 	console.log("updating values");
	// 	$scope.tickerData.data[0].data.change = 0;
	// 	$scope.tickerData.data[1].data.change = -10;
	// 	console.log($scope.tickerData);
	// 	$scope.$apply();
	// }, 10000);

	$scope.createCharts = function(data) {
		console.log("hit create charts");
		console.log(data);
		for (const tickerIdx in data) {
			const ticker = data[tickerIdx];
			const tickerName = ticker.ticker;
			// var svg = d3.select("#" + ticker + "-homeChart").append("svg").attr("width", "100%").attr("height", "100%").


			// var container = am4core.create(tickerName + "-homeChartWrapper", am4core.Container);
			// container.width = am4core.percent(50);
			// container.height = am4core.percent(100);

			var chart = am4core.create(tickerName + "-homeChartWrapper", am4charts.XYChart);
			chart.dateFormatter.inputDateFormat = "yyyy-MM-dd";

			// chart.stroke = am4core.color("rgb(215, 218, 220)");
			chart.fontSize = "0.75rem";
			chart.fontWeight = 100;
			chart.paddingLeft = 0;
			chart.paddingRight = 0;

			var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
			dateAxis.renderer.grid.template.location = 0;
			dateAxis.skipEmptyPeriods = true;

			dateAxis.renderer.grid.template.stroke = am4core.color("rgb(215, 218, 220)");
			dateAxis.renderer.labels.template.disabled = true;
			// dateAxis.renderer.labels.template.zIndex = 9999;

			var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
			valueAxis.tooltip.disabled = true;

			valueAxis.renderer.grid.template.stroke = am4core.color("rgb(215, 218, 220)");
			valueAxis.renderer.labels.template.fill = am4core.color("rgb(215, 218, 220)");

			var series = chart.series.push(new am4charts.CandlestickSeries());
			series.dataFields.dateX = "Date";
			series.dataFields.valueY = "Close";
			series.dataFields.openValueY = "Open";
			series.dataFields.lowValueY = "Low";
			series.dataFields.highValueY = "High";
			series.simplifiedProcessing = true;
			series.tooltipText = "Open: ${openValueY.value}\nLow: ${lowValueY.value}\nHigh: ${highValueY.value}\nClose: ${valueY.value}";

			chart.cursor = new am4charts.XYCursor();

			chart.data = ticker.data.history;

			$scope.$on("$destroy", function() {
				chart.dispose();
			});
		}
	};

	$scope.updateStar = function(tickerInfo) {
		tickerInfo.star = !tickerInfo.star;
		$http.post("/updateStock", {"ticker": tickerInfo.ticker, "star": tickerInfo.star}).then(undefined, function(err) {
			console.log("failed to post /updateStock");
			console.log(err);
			alert("Failed to update ticker star");
		});
	};

	$scope.updateOwn = function(tickerInfo) {
		tickerInfo.own = !tickerInfo.own;
		$http.post("/updateStock", {"ticker": tickerInfo.ticker, "own": tickerInfo.own}).then(undefined, function(err) {
			console.log("failed to post /updateStock");
			console.log(err);
			alert("Failed to update ticker own");
		});
	};

	$scope.updateNotes = function(tickerName, notes) {
		$http.post("/updateStock", {"ticker": tickerName, "notes": notes}).then(undefined, function(err) {
			console.log("failed to post /updateStock");
			console.log(err);
			alert("Failed to update ticker notes");
		});
		return;
	};

	$scope.gotoResearch = function(tickerInfo) {
		console.log("going to research");
		$rootScope.$emit("loadResearch", tickerInfo);
		$location.hash("research");
	};

}]);