// app.controller('NavCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$window', '$http', '$compile',
// 	function($scope, $rootScope, $timeout, $location, $window, $http, $compile) {
app.controller('NavCtrl', ['$scope', '$location', '$window', '$http',
	function($scope, $location, $window, $http) {

	$scope.activeId = "";
	$scope.tabIds = [	//these are the ids from main div of each page
		"#homeDiv",
		"#researchDiv",
		"#exploreDiv"
	];

	//add a listener for the nav bar
	$scope.$on('$locationChangeSuccess', function() {
		var hash = $location.hash();
		$("#mainNavbar .active").removeClass("active");

		if (hash == 'home') {
			$scope.activeId = "#homeDiv";
			$("#homeNavbar").addClass("active");
		}
		else if (hash == 'research') {
			$scope.activeId = "#researchDiv";
			$("#researchNavbar").addClass("active");
		}
		else if (hash == 'explore') {
			$scope.activeId = "#exploreDiv";
			$("#exploreNavbar").addClass("active");
		}
		else if (hash == "logout") {
			$http.post("/logout").then(function(resp) {
				// $timeout(function () {
					$window.location.href = '/';
				// });
			}, function(err) {
				alert("Session expired");
				$window.location.href = '/';
			});
		}
		else {
			//default screen here
			//route to home
			$scope.activeId = "#homeDiv";
			$("#homeNavbar").addClass("active");
		}

		$scope.tabIds.forEach(function(tabId) {
			if (tabId == $scope.activeId) {
				$(tabId).show();
			} else {
				$(tabId).hide();
			}
		});
	});
}]);
