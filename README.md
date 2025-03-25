# Barbershop Booking

## Introduzione

Il progetto "Barbershop Booking" è un sistema di prenotazione online sviluppato con Flask e SQLite, pensato per gestire in modo efficiente gli appuntamenti in attività come i saloni da barbiere. Il sistema offre funzionalità per utenti e amministratori, consentendo la registrazione, il login, la prenotazione, la modifica e la cancellazione degli appuntamenti.

## Caratteristiche

- **Homepage:** Punto d’ingresso con opzioni per login utente, login admin e registrazione.
- **Prenotazione Appuntamenti:** Gli utenti possono prenotare un appuntamento selezionando il servizio, la data e l’orario desiderati. Il sistema verifica la disponibilità per evitare sovrapposizioni.
- **Gestione Utente:** Gli utenti registrati possono visualizzare, modificare e cancellare le proprie prenotazioni tramite un dashboard dedicato.
- **Dashboard Amministratore:** Il personale amministrativo può visualizzare tutte le prenotazioni e gestirle, garantendo un controllo completo sui processi.
- **Interazione Dinamica:** Utilizzo della Fetch API per operazioni asincrone, come la cancellazione degli appuntamenti senza ricaricare la pagina.
- **Design Responsivo:** Implementazione di layout e stili personalizzati tramite HTML e CSS (con media query) per garantire una visualizzazione ottimale su desktop e dispositivi mobili.

## Requisiti

- Python 3.x
- Flask
- SQLite (incluso nella libreria standard di Python)

Le dipendenze sono specificate nel file `requirements.txt`.

Le credenziali di accesso per l'Admin sono nome utente "admin" password: "admin"

## Installazione e Configurazione

1. **Clonare il repository:**

   ```bash
   git clone https://github.com/michelerubinic/barber_booking.git
   cd barber_booking

---------------------------------

# Barbershop Booking - Sistema di Prenotazione

## 📌 Introduzione
Sistema di prenotazione per un barbiere, sviluppato con Flask e SQLite, che consente agli utenti di prenotare appuntamenti scegliendo solo tra i servizi disponibili.

## ✅ Funzionalità principali
- **Login/Logout** per utenti e amministratori nome utente: ADMIN passw: ADMIN
- **Registrazione utenti**
- **Prenotazione Appuntamenti** con scelta del servizio, giorno e fascia oraria
- **Gestione Appuntamenti Utente**: modifica o cancellazione
- **Dashboard Admin**: visualizza e gestisce tutti gli appuntamenti
- **Verifica automatica disponibilità** con blocco delle fasce orarie occupate
- **Completamente responsive** su desktop e mobile

## 💈 Servizi disponibili (selezionabili dall'utente):
- Taglio di capelli
- Taglio di capelli + Barba
- Solo Barba

✅ **Solo questi servizi possono essere prenotati**  
✅ **Scelta dell'orario tra le 09:00 e le 19:00 in slot di 30 minuti**

## 🛠 Requisiti
- Python 3.x
- Flask
- SQLite

Installa le dipendenze con:
```bash
pip install -r requirements.txt
