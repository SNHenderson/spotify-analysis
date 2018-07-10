function changeTheme() {
    var e = document.getElementById("select");
    var theme = e.options[e.selectedIndex].value;
    localStorage.setItem('theme', theme);
    document.body.className = theme;
}

window.addEventListener("load", function() {
    document.getElementById("select").addEventListener("change", function() {
        changeTheme();
    });

    var theme = localStorage.getItem('theme');
    if(theme) {
        document.getElementById("select").value = theme;
        document.body.className = theme;
    }
});
