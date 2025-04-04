document.addEventListener('DOMContentLoaded', function () {
  // === UTENTE o ADMIN (lista appuntamenti) ===
  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('delete-appointment')) {
      const id = e.target.dataset.id;
      if (!id) {
        alert('ID appuntamento mancante.');
        return;
      }

      if (confirm('Sei sicuro di voler eliminare questo appuntamento?')) {
        fetch(`/delete_appointment/${id}`, {
          method: 'POST',
          credentials: 'include'
        })
        .then(res => {
          if (res.ok) {
            location.reload();
          } else if (res.status === 403) {
            alert("❌ Non puoi cancellare un appuntamento passato.");
          } else {
            alert(`Errore durante l'eliminazione. Codice: ${res.status}`);
          }
        })
        .catch(() => {
          alert('Errore di rete durante l\'eliminazione.');
        });
      }
    }
  });

  // === ADMIN (cestino nella vista calendario) ===
  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('admin-delete-appointment')) {
      const id = e.target.dataset.id;
      if (!id) {
        alert('ID appuntamento mancante.');
        return;
      }

      if (confirm('Vuoi eliminare questo appuntamento dal calendario?')) {
        fetch(`/admin_delete_appointment/${id}`, {
          method: 'POST',
          credentials: 'include'
        })
        .then(res => {
          if (res.ok) {
            location.reload();
          } else {
            alert(`Errore durante l'eliminazione. Codice: ${res.status}`);
          }
        })
        .catch(() => {
          alert('Errore di rete durante l\'eliminazione.');
        });
      }
    }
  });
});
