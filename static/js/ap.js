document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll(".dropdown-submenu").forEach(function (el) {

        const submenu = el.querySelector(".dropdown-menu");

        el.addEventListener("mouseenter", function () {
            if (submenu) submenu.classList.add("show");
        });

        el.addEventListener("mouseleave", function () {
            if (submenu) submenu.classList.remove("show");
        });

        el.addEventListener("click", function (e) {
            e.stopPropagation();
            if (submenu) submenu.classList.toggle("show");
        });

    });

});
document.getElementById("select-all").addEventListener("change", function () {
    document.querySelectorAll(".produit-check").forEach(function (checkbox) {
        checkbox.checked = document.getElementById("select-all").checked;
    });
});