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

	getTickerData();	//initial load in of data; TODO: surround this with loading spinner!

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
	};

	$scope.gotoResearch = function(tickerInfo) {
		console.log("going to research");
		$rootScope.$emit("loadResearch", tickerInfo);
		$location.hash("research");
	};

}]);