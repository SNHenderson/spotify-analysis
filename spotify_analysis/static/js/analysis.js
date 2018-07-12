const postData = (url = '', data = {}) => {
  // Default options are marked with *
    return fetch(url, {
        method: "POST", // *GET, POST, PUT, DELETE, etc.
        mode: "cors", // no-cors, cors, *same-origin
        cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
        credentials: "same-origin", // include, same-origin, *omit
        headers: {
            "Content-Type": "application/json; charset=utf-8",
        },
        redirect: "follow", // manual, *follow, error
        referrer: "no-referrer", // no-referrer, *client
        body: JSON.stringify(data), // body data type must match "Content-Type" header
    })
    .then(response => response.json()) // parses response to JSON
    .catch(error => console.error(`Fetch Error =\n`, error));
};

window.addEventListener("load", function() {
    function load() {
        var FD = new FormData(loadForm);
        var data = {};
       
        FD.forEach(function(value, key){
            data[key] = value;
        });

        document.getElementById("songs-table").classList.add('d-none');
        document.getElementById("tbody").innerHTML = "";
        document.getElementById("status").innerHTML = "Loading songs..."

        postData('/api/load/', data)
        .then(function(response) {
            if(response['success']) {
                document.getElementById("status").innerHTML = "Loaded data: <a href=\"/data/" + data['name'] + "\"> " + data['name'] + " </a>";
            } else {
                document.getElementById("status").innerHTML = "Error loading data";
                console.error(response);
            }
        }).catch(error => console.error(error));
    }

    function learn() {
        var FD = new FormData(learnForm);

        document.getElementById("songs-table").classList.add('d-none');
        document.getElementById("tbody").innerHTML = "";
        document.getElementById("status").innerHTML = "Training model..."

        fetch('/api/learn/' + FD.get('name'))
        .then((response) => response.json()) 
        .then(function(data) {
            if(data['success']) {
                document.getElementById("status").innerHTML = "Trained model, test mismatched: " + data["test_outliers_%"].toFixed(2) + "%";
            } else {
                document.getElementById("status").innerHTML = "Error training model";
                console.error(data);
            }
        }).catch(error => console.error(error));
    }

    function predict() {
        var FD = new FormData(predictForm);

        var data = {};
       
        FD.forEach(function(value, key){
            data[key] = value;
        });

        document.getElementById("songs-table").classList.add('d-none');
        document.getElementById("status").innerHTML = "Loading songs and predicting..."
        var tbody = document.getElementById("tbody");
        tbody.innerHTML = "";

        postData('/api/predict/', data)
        .then(function(data) { 
            if(tbody.innerHTML != "") {
                tbody.innerHTML = "";
            }
            var songs = data["inliers"];
            
            if(songs && Object.keys(songs).length > 0) {
                document.getElementById("songs-table").classList.remove('d-none');
            }

            for (var i in songs) {
                var tr = "<tr>";
                tr += "<td>" + songs[i]["name"] + "</td>";
                tr += "<td>" + songs[i]["acousticness"] + "</td>";
                tr += "<td>" + songs[i]["danceability"] + "</td>";
                tr += "<td>" + songs[i]["duration_ms"] + "</td>";
                tr += "<td>" + songs[i]["energy"] + "</td>";
                tr += "<td>" + songs[i]["instrumentalness"] + "</td>";
                tr += "<td>" + songs[i]["key"] + "</td>";
                tr += "<td>" + songs[i]["liveness"] + "</td>";
                tr += "<td>" + songs[i]["loudness"] + "</td>";
                tr += "<td>" + songs[i]["mode"] + "</td>";
                tr += "<td>" + songs[i]["popularity"] + "</td>";
                tr += "<td>" + songs[i]["speechiness"] + "</td>";
                tr += "<td>" + songs[i]["tempo"] + "</td>";
                tr += "<td>" + songs[i]["time_signature"] + "</td>";
                tr += "<td>" + songs[i]["valence"] + "</td>";

                tbody.innerHTML += tr;
            }
            songs = [];
            if(data['success']) {
                document.getElementById("status").innerHTML = "Songs classified under trained model: " + data["inliers_count"] + ", " + data["inliers_%"].toFixed(2) + "%";
            } else {
                document.getElementById("status").innerHTML = "Error predicting, make sure the model is trained";
                console.error(data);
            }
        }) 
        .catch(error => console.error(error));
    }

    var loadForm = document.getElementById("load");
    var learnForm = document.getElementById("learn");
    var predictForm = document.getElementById("predict");

    loadForm.addEventListener("submit", function(event) {
        event.preventDefault();
        load();
    });

    learnForm.addEventListener("submit", function(event) {
        event.preventDefault();
        learn();
    });

    predictForm.addEventListener("submit", function(event) {
        event.preventDefault();
        predict();
    });

    var setters = document.querySelectorAll(".setter");
    
    for (var i = 0; i < setters.length; i++) {
        (function () {
            var set = setters[i];
            set.addEventListener("click", function () {
                var id = set.title;
                document.getElementById(id).value = set.innerHTML;
            });
        }());
    }
});
