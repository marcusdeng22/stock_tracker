var app = angular.module('LoginApp', []);

app.controller('LoginCtrl', ['$scope', '$http', '$window', function($scope, $http, $window) {

	$scope.username = "";
	$scope.password = "";
	$scope.newPassword = "";
	$scope.verifyPassword = "";

	$("#usernameInput").focus();

	$scope.doLogin = function() {
		$http.post('/doLogin', {"username": $scope.username, "password": $scope.password}).then(function(resp) {
			$window.location.href = '/';
		}, function(err) {
			$scope.username = "";
			$scope.password = "";
			alert("Login failure");
			$("#usernameInput").focus();
		});
	};

	$scope.doChange = function() {
		if ($scope.newPassword != $scope.verifyPassword) {
			return;
		}
		$http.post("/changePassword", {"username": $scope.username, "old": $scope.password, "new": $scope.newPassword}).then(function(resp) {
			alert("Password successfully changed!");
			//redirect back to login
			$window.location.href = "/";
		}, function(err) {
			alert("Failed to change password");
		});
	};

}]);