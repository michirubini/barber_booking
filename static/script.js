document.addEventListener("DOMContentLoaded", function () {
    function deleteAppointment(appointmentId) {
        if (!confirm("Sei sicuro di voler eliminare questo appuntamento?")) {
            return;
        }

        fetch(`/delete_appointment/${appointmentId}`, {
            method: 'POST',
            headers: { "Content-Type": "application/json" }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Appuntamento eliminato con successo.");
                location.reload();
            } else {
                alert("Errore: " + data.message);
            }
        })
        .catch(error => {
            console.error("Errore:", error);
            alert("Errore durante l'eliminazione dell'appuntamento.");
        });
    }

    document.querySelectorAll(".delete-appointment").forEach(button => {
        button.addEventListener("click", function () {
            const appointmentId = this.dataset.id;
            deleteAppointment(appointmentId);
        });
    });
});
