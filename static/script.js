document.addEventListener('DOMContentLoaded', function () {
    // Gestione eliminazione appuntamenti (sia da lista che da calendario)
    document.querySelectorAll('.delete-appointment').forEach(btn => {
      btn.addEventListener('click', function () {
        const id = this.dataset.id;
        if (confirm('Sei sicuro di voler eliminare questo appuntamento?')) {
          fetch(`/delete_appointment/${id}`, {
            method: 'POST'
          }).then(res => {
            if (res.status === 204) {
              location.reload();
            } else {
              alert('Errore durante l\'eliminazione.');
            }
          });
        }
      });
    });
  });
  