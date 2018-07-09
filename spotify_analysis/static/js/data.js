function changeTheme() {
    var e = document.getElementById("select");
    var theme = e.options[e.selectedIndex].value;
    localStorage.setItem('theme', theme);
    document.body.className = theme;
}

window.addEventListener("load", function() {
    var theme = localStorage.getItem('theme');
    if(theme) {
        document.getElementById("select").value = theme;
        document.body.className = theme;
    }

    function load() {
        var name = document.getElementById("name").innerHTML;
        fetch('/api/data/' + name + ".pkl")
        .then((response) => response.json()) 
        .then(function(data) {
            var p = document.getElementById("figures");
            var figures = data["figures"];
            
            for (var i = 0; i < figures.length; i++) {
                p.innerHTML += "<img class=\"invert\" src=\"data:image/png;base64," + figures[i] + "\">"
            }
            document.getElementById("status").classList.add('d-none');
        }).catch(error => console.error(error));
    }

    load();
});
