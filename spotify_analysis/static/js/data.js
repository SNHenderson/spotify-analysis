window.addEventListener("load", function() {
    function load() {
        var name = document.getElementById("name").innerHTML;
        fetch('/api/data/' + name + ".pkl")
        .then((response) => response.json()) 
        .then(function(data) {
            var p = document.getElementById("figures");
            var figures = data["figures"];
            
            for (var i = 0; i < figures.length; i++) {
                p.innerHTML += "<img class=\"img-fluid invert\" src=\"data:image/png;base64," + figures[i] + "\">"
            }
            document.getElementById("status").classList.add('d-none');
        }).catch(error => console.error(error));
    }

    load();
});
