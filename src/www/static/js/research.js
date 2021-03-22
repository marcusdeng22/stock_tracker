app.controller('researchCtrl', ['$scope', '$rootScope', '$location', '$window', '$http', '$timeout',
	function($scope, $rootScope, $location, $window, $http, $timeout) {
		$scope.searchText = "";
		$scope.searchResults = [];

		$scope.ticker = {};	//stores ticker information

		$scope.searching = false;

		$scope.searchTicker = function() {
			if ($scope.searchText.length == 0) {
				$scope.searchResults = [];
				return;
			}
			//post to server $scope.searchText and store results in $scope.searchResults
			$scope.searching = true;
			$http.post("/searchText", {data: $scope.searchText}).then(function(resp) {
				console.log("done searching");
				$scope.searching = false;
				$scope.searchResults = resp["data"]["data"];
			}, function(err) {
				$scope.searching = false;
				console.log("failed to post /searchText");
				console.log(err);
				alert("Failed to search text");
			});
		};

		$scope.submitTicker = function(idx, enter=false) {
			// $scope.searchText = tickerName;
			console.log("submitTicker", idx, enter, $scope.searching, $scope.searchText);
			if (enter) {
				console.log("watching");
				$scope.searching = true;
				//watch until we are done searching
				//from: https://stackoverflow.com/questions/15715672/how-do-i-stop-watching-in-angularjs
				var unregister = $scope.$watch("searching", function() {
					console.log("watch hit", $scope.searching);
					if ($scope.searching == false) {
						console.log("watch done");
						$scope.submitTicker(idx);
						unregister();
					}
				});
				return;
			}
			if (idx < $scope.searchResults.length) {
				console.log($scope.searchResults[idx])
				//post to server to grab ticker info
				var tickerName = $scope.searchResults[idx].ticker;
				$scope.searchText = "";
				$scope.searchResults = [];
				$http.post("/checkStock", {"ticker": tickerName}).then(function(resp) {
					console.log("returned check stock");
					$scope.ticker = resp["data"]["data"];
				}, function(err) {
					console.log("failed to post /checkStock");
					console.log(err);
					alert("Failed to search ticker");
				});
			}
		};

		$scope.updateNotes = function(tickerName, notes) {
			return;
		};

		$scope.addDB = function(tickerData) {
			console.log("adding to db:", tickerData);
			$http.post("/addStock", {
				ticker: tickerData.ticker,
				own: tickerData.own,
				star: tickerData.star,
				notes: tickerData.notes
			}).then(function(resp) {
				console.log("added ticker", tickerData.ticker);
				tickerData.indb = true;
				//TODO: notify homelist to send a refresh to grab the new data
			}, function(err) {
				console.log("failed to post /addStock");
				console.log(err);
				alert("Failed to add ticker");
			});
		};

		$rootScope.$on("loadResearch", function(e, tickerData) {
			//load tickerData into all fields
			$scope.ticker = tickerData;
			// $scope.searchText = tickerData.ticker;	//TODO: do we set this or clear this?
			$scope.searchText = "";
			console.log($scope.ticker);
		});
}])
.filter("isEmpty", function() {
	return function(obj) {
		return angular.equals({}, obj);
	};
});