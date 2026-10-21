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

document.addEventListener("DOMContentLoaded", function () {

    // ================= CONTACT =================
    const addContactBtn = document.getElementById("add-contact");
    const contactTable = document.getElementById("contact-table").getElementsByTagName('tbody')[0];
    const totalContacts = document.getElementById("id_contactclient_set-TOTAL_FORMS");

    addContactBtn.addEventListener("click", function () {

        let formIdx = parseInt(totalContacts.value);
        let emptyForm = document.querySelector("#empty-contact-form tr").cloneNode(true);

        emptyForm.innerHTML = emptyForm.innerHTML.replace(/__prefix__/g, formIdx);

        contactTable.appendChild(emptyForm);
        totalContacts.value = formIdx + 1;
    });


    // ================= COMPTE =================
    const addCompteBtn = document.getElementById("add-compte");
    const compteTable = document.getElementById("compte-table").getElementsByTagName('tbody')[0];
    const totalComptes = document.getElementById("id_comptebancaire_set-TOTAL_FORMS");

    addCompteBtn.addEventListener("click", function () {

        let formIdx = parseInt(totalComptes.value);
        let emptyForm = document.querySelector("#empty-compte-form tr").cloneNode(true);

        emptyForm.innerHTML = emptyForm.innerHTML.replace(/__prefix__/g, formIdx);

        compteTable.appendChild(emptyForm);
        totalComptes.value = formIdx + 1;
    });

});