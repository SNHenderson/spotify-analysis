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
    function clearData() {
        songs = [];
        page = 0;
        document.getElementById("results").classList.add('d-none');
        document.getElementById("tbody").innerHTML = "";
    }
    function load() {
        var FD = new FormData(loadForm);
        var data = {};
       
        FD.forEach(function(value, key){
            data[key] = value;
        });

        clearData();
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

        clearData();
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

    var songs = [];
    var page = 0;
    var show = 25;

    function setHTMLandListeners() {
        var pagination = document.getElementById("pagination");

        pagination.innerHTML = "<li class=\"page-item disabled\" id=\"previous\"><a class=\"page-link bg-light\">Previous</a></li>"
        var totalPages = songs.length / show;
        var pageOffset = Math.max(0, page - 5);
        for (var i = pageOffset; i < pageOffset + 10 && i < totalPages; i++) {
            pagination.innerHTML += "<li id=\"page-" + i + "\" class=\"page-item\"><a class=\"page-link bg-light numeric\">" + (i+1) + "</a></li>"
        }
        pagination.innerHTML += "<li class=\"page-item\" id=\"next\"><a class=\"page-link bg-light\">Next</a></li>"

        prevButton = document.getElementById("previous");
        nextButton = document.getElementById("next");

        prevButton.addEventListener("click", function(event) {
            prev();
        });

        nextButton.addEventListener("click", function(event) {
            next();
        });

        var numberLinks = document.querySelectorAll(".numeric");
    
        for (var i = 0; i < numberLinks.length; i++) {
            (function () {
                var link = numberLinks[i];
                link.classList.remove('active');
                link.addEventListener("click", function () {
                    page = parseInt(link.text) - 1;
                    populateSongs();
                });
            }());
        }

        document.getElementById("page-" + page).classList.add('active');
    }

    function populateSongs() {
        if (songs && songs.length > 0) {
            setHTMLandListeners();

            tbody.innerHTML = "";
            document.getElementById("results").classList.remove('d-none');
            saveButton.classList.remove('d-none');
            if(page * show + show >= songs.length) {
                nextButton.classList.add('disabled');
            } else {
                nextButton.classList.remove('disabled');
            }
            if(page > 0) {
                prevButton.classList.remove('disabled');
            } else {
                prevButton.classList.add('disabled');
            }
        }

        for (var i = page * show; i < (page * show) + show && i < songs.length; i++) {
            var tr = "<tr>";
            tr += "<td>" + songs[i]["name"] + "</td>";
            tr += "<td>" + songs[i]["acousticness"] + "</td>";
            tr += "<td>" + songs[i]["danceability"] + "</td>";
            // tr += "<td>" + songs[i]["duration_ms"] + "</td>";
            tr += "<td>" + songs[i]["energy"] + "</td>";
            tr += "<td>" + songs[i]["instrumentalness"] + "</td>";
            // tr += "<td>" + songs[i]["key"] + "</td>";
            tr += "<td>" + songs[i]["liveness"] + "</td>";
            tr += "<td>" + songs[i]["loudness"] + "</td>";
            // tr += "<td>" + songs[i]["mode"] + "</td>";
            tr += "<td>" + songs[i]["popularity"] + "</td>";
            tr += "<td>" + songs[i]["speechiness"] + "</td>";
            tr += "<td>" + songs[i]["tempo"] + "</td>";
            // tr += "<td>" + songs[i]["time_signature"] + "</td>";
            tr += "<td>" + songs[i]["valence"] + "</td>";

            tbody.innerHTML += tr;
        }
    }

    function next() {
        if(page * show + show < songs.length) {
            page += 1;
            populateSongs();
        }
    }

    function prev() {
        if(page > 0) {
            page -= 1;
            populateSongs();
        }
    }

    function predict() {
        var FD = new FormData(predictForm);

        var data = {};
       
        FD.forEach(function(value, key){
            data[key] = value;
        });

        clearData();
        document.getElementById("status").innerHTML = "Loading songs and predicting..."
        var tbody = document.getElementById("tbody");
        tbody.innerHTML = "";

        postData('/api/predict/', data)
        .then(function(data) { 
            tbody.innerHTML = "";
            if(data['inliers']) {
                songs = Object.values(data["inliers"]);
                populateSongs();
            }
            
            if(data['success']) {
                document.getElementById("status").innerHTML = "Songs classified under trained model: " + data["inliers_count"] + ", " + data["inliers_%"].toFixed(2) + "%";
            } else {
                document.getElementById("status").innerHTML = "Error predicting, make sure the model is trained";
                console.error(data);
            }
        }) 
        .catch(error => console.error(error));
    }

    function save() {
        var FD = new FormData(predictForm);

        document.getElementById("status").innerHTML = "Saving playlist..."
        saveButton.classList.add('d-none');

        var data = {};
       
        FD.forEach(function(value, key){
            data[key] = value;
        });

        postData('/api/save/', data)
        .then(function(data) {
            if(data['success']) {
                document.getElementById("status").innerHTML = "Saved playlist";
            } else {
                document.getElementById("status").innerHTML = "Error saving playlist";
                console.error(data);
            }
        }).catch(error => console.error(error));
    }

    var loadForm = document.getElementById("load");
    var learnForm = document.getElementById("learn");
    var predictForm = document.getElementById("predict");
    var saveButton = document.getElementById("save");
    var prevButton;
    var nextButton;

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

    saveButton.addEventListener("click", function(event) {
        save();
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
