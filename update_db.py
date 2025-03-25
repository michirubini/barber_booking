import sqlite3

# Connessione al database
conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

try:
    # Aggiungo le colonne SOLO se non esistono (se lanci 2 volte, va in errore ma la prima va a buon fine)
    cursor.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT 'NOME'")
    print("[OK] Colonna 'name' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'name' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN surname TEXT NOT NULL DEFAULT 'COGNOME'")
    print("[OK] Colonna 'surname' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'surname' esiste già")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT '0000000000'")
    print("[OK] Colonna 'phone' aggiunta")
except sqlite3.OperationalError:
    print("[INFO] La colonna 'phone' esiste già")

conn.commit()
conn.close()
print("✅ Database aggiornato con successo!")
