from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ---------- INIZIALIZZAZIONE DB ----------
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- ROTTE PRINCIPALI ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_delete_appointment/<int:appointment_id>', methods=['POST'])
def admin_delete_appointment(appointment_id):
    if 'admin' not in session:
        return '', 403

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return '', 204


@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        # ✅ Se sei loggato come utente, esci dalla sessione utente
        session.pop('user_id', None)
        session.pop('username', None)

        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login_admin.html', error="Credenziali admin non valide")
    return render_template('login_admin.html')


@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        # ✅ Se sei loggato come admin, esci dalla sessione admin
        session.pop('admin', None)

        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('user_dashboard'))
        else:
            return render_template('login_user.html', error="Credenziali non valide")
    return render_template('login_user.html')


@app.route('/admin_users')
def admin_users():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, surname, phone, email, username FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    
    return render_template('admin_users.html', users=users)

@app.route('/admin_delete_selected_users', methods=['POST'])
def delete_selected_users():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    selected_ids = request.form.getlist('selected_users')
    if selected_ids:
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Prima cancella gli appuntamenti legati
        cursor.executemany("DELETE FROM appointments WHERE user_id = ?", [(uid,) for uid in selected_ids])
        # Poi elimina gli utenti
        cursor.executemany("DELETE FROM users WHERE id = ?", [(uid,) for uid in selected_ids])

        conn.commit()
        conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin_edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Controlli duplicati
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password),
                                   error="Username già in uso")

        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password),
                                   error="Email già registrata")

        # Salva modifiche
        cursor.execute("""
            UPDATE users 
            SET name = ?, surname = ?, phone = ?, email = ?, username = ?, password = ?
            WHERE id = ?
        """, (name, surname, phone, email, username, password, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))

    # Carica dati utente
    cursor.execute("SELECT name, surname, phone, email, username, password FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return redirect(url_for('admin_users'))

    return render_template('admin_edit_user.html', user=user)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for('index'))



@app.route('/admin_delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_users'))




# ---------- ALTRE FUNZIONI UTILI ----------

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def invia_email_registrazione(destinatario, nome, cognome, username, telefono, password):
    mittente = 'rubinimc@gmail.com'  # o la mail definitiva del salone
    password_email = 'mtgk jhxz wagn wicg'

    oggetto = "Benvenuto da Les Klips Hair & Barber – Registrazione completata"
    messaggio = f"""
Ciao {nome} {cognome},

Grazie per esserti registrato/a presso Les Klips Hair & Barber!
Siamo felici di averti con noi.

Ecco i tuoi dati di accesso personali:

• Username: {username}
• Password: {password}
• Email: {destinatario}
• Telefono: {telefono}

Potrai ora prenotare facilmente i tuoi appuntamenti direttamente online.

Per modifiche o cancellazioni puoi gestire tutto dal sito, oppure chiamare il numero: 051 683 0322 📞

Per qualsiasi altra informazione, siamo a tua disposizione.

A presto,  
Il team Les Klips Hair & Barber
"""


    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = oggetto
    msg.attach(MIMEText(messaggio, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password_email)
        server.send_message(msg)
        server.quit()
        print("📨 Email inviata con successo!")
    except Exception as e:
        print("❌ Errore nell'invio dell'email:", e)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Controllo se le password coincidono
        if password != confirm_password:
            return render_template('register.html', error="Le password non coincidono.")

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # ❌ Controllo username già esistente
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Username già esistente")

        # ❌ Controllo email già registrata
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Email già registrata")

        # ✅ Inserimento nuovo utente
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, name, surname, phone, email))

        conn.commit()
        conn.close()

        # ✅ Invio email di conferma registrazione
        invia_email_registrazione(email, name, surname, username, phone, password)

        return redirect(url_for('login_user'))

    return render_template('register.html')


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    cursor.execute("""
        SELECT id, service, date, time
        FROM appointments
        WHERE user_id = ? AND (date > ? OR (date = ? AND time >= ?))
        ORDER BY date ASC, time ASC
    """, (user_id, today, today, now_time))

    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_dashboard.html', appointments=appointments)

@app.route('/user_history')
def user_history():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT service, date, time
        FROM appointments
        WHERE user_id = ? AND (date < ? OR (date = ? AND time < ?))
        ORDER BY date DESC, time DESC
    """, (user_id, today, today, now_time))

    appointments = cursor.fetchall()
    conn.close()

    return render_template('user_history.html', appointments=appointments)
@app.route('/admin_hourly_calendar')
def admin_hourly_calendar():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    return render_template('admin_calendar_hourly.html')


@app.route('/admin_add_user', methods=['GET', 'POST'])
def admin_add_user():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Verifica duplicati
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password),
                                   error="Username già esistente")

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return render_template('admin_edit_user.html', user=(name, surname, phone, email, username, password),
                                   error="Email già registrata")

        # Inserimento
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, name, surname, phone, email))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))

    # GET – form vuoto
    user = ("", "", "", "", "", "")
    return render_template('admin_edit_user.html', user=user)


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.commit()
    cursor.execute("""
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time, appointments.barber
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date >= ?
        ORDER BY DATE(appointments.date), TIME(appointments.time)
    """, (today,))
    appointments = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', appointments=appointments)

from flask import request, session, redirect, url_for, render_template
from datetime import datetime, timedelta
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_obj = datetime.strptime(time, "%H:%M").time()
            now = datetime.now()

            if date_obj.date() < now.date():
                return render_template('book.html', error="Non puoi prenotare in una data passata.")
            if date_obj.date() == now.date():
                appointment_datetime = datetime.combine(date_obj.date(), time_obj)
                if appointment_datetime < now + timedelta(hours=1):
                    return render_template('book.html', error="Devi prenotare almeno un'ora prima.")
            if date_obj.weekday() < 1 or date_obj.weekday() > 5:
                return render_template('book.html', error="Prenotabile solo da martedì a sabato.")
            if date_obj.weekday() == 5 and time > '15:00':
                return render_template('book.html', error="Sabato solo fino alle 15:00.")
        except:
            return render_template('book.html', error="Data o orario non validi.")

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT barber FROM appointments
            WHERE date = ? AND time = ?
        """, (date, time))
        booked_barbers = [row[0] for row in cursor.fetchall()]

        assigned_barber = None
        for b in ['Achille', 'Mattia']:
            if b not in booked_barbers:
                assigned_barber = b
                break

        if not assigned_barber:
            conn.close()
            return render_template('book.html', error="Orario già pieno.")

        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, assigned_barber))

        conn.commit()

        # 📧 Invia email
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = ?", (user_id,))
            user_info = cursor.fetchone()
            if user_info and user_info[1]:
                invia_email_appuntamento(
                    destinatario=user_info[1],
                    nome=user_info[0],
                    telefono=user_info[2],
                    email=user_info[1],
                    servizio=service,
                    data=date,
                    ora=time,
                    barbiere=assigned_barber
                )
        except Exception as e:
            print("❌ Errore nell'invio email appuntamento:", e)

        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book.html')


def invia_email_appuntamento(destinatario, nome, telefono, email, servizio, data, ora, barbiere=None):
    mittente = 'rubinimc@gmail.com'
    password = 'mtgk jhxz wagn wicg'  # Cambia con una password sicura

    # ---- Email al cliente ----
    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = "Conferma appuntamento – Les Klips Hair & Barber"

    corpo = f"""
Ciao {nome},

la tua prenotazione è stata confermata ✅

✂️ Servizio: {servizio}
📅 Data: {data}
⏰ Ora: {ora}

Ti aspettiamo da Les Klips Hair & Barber! 💈

Per modifiche o cancellazioni puoi farlo direttamente dal sito, oppure contattaci al numero: 051 683 0322 📞

— Lo staff di Les Klips
"""
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mittente, password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("❌ Errore invio email cliente:", e)

    # ---- Copia al salone ----
    msg_salone = MIMEMultipart()
    msg_salone['From'] = mittente
    msg_salone['To'] = 'rubinimc@gmail.com'
    msg_salone['Subject'] = "📅 Nuova prenotazione ricevuta"

    corpo_salone = f"""
📬 Nuova prenotazione ricevuta!

👤 Cliente: {nome}
📞 Cellulare: {telefono}
📧 Email: {email}

✂️ Servizio: {servizio}
📅 Data: {data}
⏰ Ora: {ora}
💈 Barbiere: {barbiere or 'Non specificato'}

Controlla il gestionale per i dettagli.
"""
    msg_salone.attach(MIMEText(corpo_salone, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mittente, password)
        server.send_message(msg_salone)
        server.quit()
    except Exception as e:
        print("❌ Errore invio email salone:", e)


@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session and 'admin' not in session:
        return redirect(url_for('login_user'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # 🔍 Carica appuntamento
    if 'admin' in session:
        cursor.execute("SELECT id, service, date, time, barber FROM appointments WHERE id = ?", (appointment_id,))
    else:
        cursor.execute("SELECT id, service, date, time, barber FROM appointments WHERE id = ? AND user_id = ?",
                       (appointment_id, session['user_id']))

    appointment = cursor.fetchone()
    if not appointment:
        conn.close()
        return redirect(url_for('admin_dashboard' if 'admin' in session else 'user_dashboard'))

    # ⛔️ Blocco modifica troppo vicina per l'utente
    if 'user_id' in session:
        appointment_datetime = datetime.strptime(f"{appointment[2]} {appointment[3]}", "%Y-%m-%d %H:%M")
        if datetime.now() > appointment_datetime - timedelta(hours=1):
            conn.close()
            return render_template("edit_appointment.html", appointment=appointment,
                                   error="Non puoi modificare l'appuntamento meno di un'ora prima.")

    if request.method == 'POST':
        new_service = request.form['service']
        new_date = request.form['date']
        new_time = request.form['time']

        # ⛔️ Controllo se lo slot è pieno
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ? AND id != ?",
                       (new_date, new_time, appointment_id))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template("edit_appointment.html", appointment=appointment,
                                   error="Fascia oraria piena.")

        # 🛠️ Se admin, aggiorna anche il barbiere
        if 'admin' in session:
            new_barber = request.form['barber']
            cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ?, barber = ? WHERE id = ?",
                           (new_service, new_date, new_time, new_barber, appointment_id))
        else:
            cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ? WHERE id = ?",
                           (new_service, new_date, new_time, appointment_id))

        conn.commit()
        conn.close()

        # 🔁 Redirect: priorità all'admin
        if 'admin' in session:
            return redirect(url_for('admin_dashboard'))
        elif 'user_id' in session:
            return redirect(url_for('user_dashboard'))
        else:
            return redirect(url_for('index'))

    conn.close()
    return render_template('edit_appointment.html', appointment=appointment)



@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, date, time FROM appointments WHERE id = ?", (appointment_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'error': 'Appuntamento non trovato'}), 404

    user_id, date_str, time_str = result
    appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()

    # SE ADMIN: bypassa tutti i controlli
    if 'admin' in session:
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
        return '', 204

    # SE UTENTE LOGGATO: controlli di sicurezza
    if 'user_id' in session:
        if session['user_id'] != user_id:
            conn.close()
            return jsonify({'error': 'Non sei autorizzato'}), 403
        if now > appointment_datetime:
            conn.close()
            return jsonify({'error': 'Appuntamento già passato'}), 403
        if now > appointment_datetime - timedelta(hours=1):
            conn.close()
            return jsonify({'error': 'Meno di un\'ora all\'appuntamento'}), 403

        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
        return '', 204

    conn.close()
    return jsonify({'error': 'Non autorizzato'}), 403

@app.route('/delete_all_appointments', methods=['POST'])
def delete_all_appointments():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/get_booked_times', methods=['POST'])
def get_booked_times():
    data = request.get_json()
    date = data.get('date')

    now = datetime.now()
    is_today = date == now.strftime("%Y-%m-%d")

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT time, COUNT(*) FROM appointments WHERE date = ? GROUP BY time", (date,))
    time_counts = cursor.fetchall()
    conn.close()

    fully_booked = [row[0] for row in time_counts if row[1] >= 2]
    less_than_one_hour = []

    if is_today:
        all_times = [
            '09:00','09:30','10:00','10:30','11:00','11:30',
            '12:00','12:30','13:00','13:30','14:00','14:30',
            '15:00','15:30','16:00','16:30','17:00','17:30',
            '18:00','18:30','19:00'
        ]

        for t in all_times:
            slot_time = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
            if slot_time < now + timedelta(hours=1):
                less_than_one_hour.append(t)

    return jsonify({
        'booked_times': fully_booked,
        'not_available_today': less_than_one_hour
    })


@app.route('/admin_get_day_slots', methods=['POST'])
def admin_get_day_slots():
    if 'admin' not in session:
        return jsonify({'error': 'Non autorizzato'}), 403

    data = request.get_json()
    date = data.get('date')
    if not date:
        return jsonify({'error': 'Data mancante'}), 400
    
    # 🔒 Blocca lunedì e domenica
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    if weekday == 0 or weekday == 6:
        return jsonify({'slots': {}})  # Nessuno slot disponibile

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.name, users.phone, appointments.service, appointments.time, appointments.id, appointments.barber
        FROM appointments
        JOIN users ON users.id = appointments.user_id
        WHERE appointments.date = ?
    """, (date,))
    records = cursor.fetchall()
    conn.close()

    all_times = [
        '09:00','09:30','10:00','10:30','11:00','11:30',
        '12:00','12:30','13:00','13:30','14:00','14:30',
        '15:00','15:30','16:00','16:30','17:00','17:30',
        '18:00','18:30','19:00'
    ]

    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()

    # Sabato: solo fino alle 15:00
    if weekday == 5:
        times = [t for t in all_times if t <= '15:00']
    else:
        times = all_times

    slots = {t: [] for t in times}
    for name, phone, servizio, time, app_id, barber in records:
        if time in slots:
            slots[time].append({
                'name': name,
                'phone': phone,
                'servizio': servizio,
                'id': app_id,
                'barber': barber
            })

    return jsonify({'slots': slots})

@app.route('/admin_get_day_slots_hair', methods=['POST'])
def admin_get_day_slots_hair():
    if 'admin' not in session:
        return jsonify({'error': 'Non autorizzato'}), 403

    data = request.get_json()
    date = data.get('date')
    if not date:
        return jsonify({'error': 'Data mancante'}), 400
    
    weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    if weekday == 0 or weekday == 6:
        return jsonify({'slots': {}})

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
    SELECT users.name, users.phone, appointments.service, appointments.time, appointments.id, appointments.barber
    FROM appointments
    JOIN users ON users.id = appointments.user_id
    WHERE appointments.date = ? AND appointments.tipo = 'parrucchiera'
""", (date,))

    records = cursor.fetchall()
    conn.close()

    all_times = ['09:00','10:00','11:00','12:00','13:00','14:00',
                 '15:00','16:00','17:00','18:00','19:00']

    if weekday == 5:
        times = [t for t in all_times if t <= '15:00']
    else:
        times = all_times

    slots = {t: [] for t in times}
    for name, phone, servizio, time, app_id, barber in records:
        if time in slots:
            slots[time].append({
                'name': name,
                'phone': phone,
                'servizio': servizio,
                'id': app_id,
                'barber': barber
            })

    return jsonify({'slots': slots})


@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Verifica che lo username non sia già usato da un altro utente
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('account.html', error="Username già in uso.", user=None)

        # Aggiorna i dati dell'utente
        cursor.execute("""
            UPDATE users 
            SET name = ?, surname = ?, phone = ?, email = ?, username = ?, password = ?
            WHERE id = ?
        """, (name, surname, phone, email, username, password, user_id))
        
        conn.commit()
        conn.close()
        session['username'] = username  # Aggiorna anche in sessione
        return redirect(url_for('user_dashboard'))

    # Carica i dati attuali dell'utente (INCLUSA email)
    cursor.execute("SELECT name, surname, phone, email, username, password FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('account.html', user=user)


@app.route('/admin_history', methods=['GET', 'POST'])
def admin_history():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    filters = {
        'start_date': '',
        'end_date': '',
        'service': '',
        'search': ''
    }

    query = """
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date < date('now')
    """
    params = []

    if request.method == 'POST':
        filters['start_date'] = request.form.get('start_date', '')
        filters['end_date'] = request.form.get('end_date', '')
        filters['service'] = request.form.get('service', '')
        filters['search'] = request.form.get('search', '')

        if filters['start_date']:
            query += " AND appointments.date >= ?"
            params.append(filters['start_date'])

        if filters['end_date']:
            query += " AND appointments.date <= ?"
            params.append(filters['end_date'])

        if filters['service']:
            query += " AND appointments.service = ?"
            params.append(filters['service'])

        if filters['search']:
            query += " AND (users.name LIKE ? OR users.surname LIKE ? OR users.phone LIKE ?)"
            like = f"%{filters['search']}%"
            params.extend([like, like, like])

    query += " ORDER BY DATE(appointments.date) DESC, TIME(appointments.time) DESC"

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    appointments = cursor.fetchall()
    conn.close()

    return render_template('admin_history.html', appointments=appointments, filters=filters)

@app.route('/admin_stats')
def admin_stats():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Appuntamenti per giorno
    cursor.execute("""
        SELECT date, COUNT(*) 
        FROM appointments 
        GROUP BY date 
        ORDER BY date
    """)
    daily_data = cursor.fetchall()

    # Appuntamenti per mese (yyyy-mm)
    cursor.execute("""
        SELECT SUBSTR(date, 1, 7) as month, COUNT(*)
        FROM appointments
        GROUP BY month
        ORDER BY month
    """)
    monthly_data = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_stats.html',
        daily_data=daily_data,
        monthly_data=monthly_data
    )

@app.route('/admin_history/export', methods=['POST'])
def export_history_csv():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    query = """
        SELECT appointments.id, users.username, users.name, users.surname, users.phone,
               appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date < date('now')
    """
    params = []

    # Recupera filtri dal form
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    service = request.form.get('service', '')
    search = request.form.get('search', '')

    if start_date:
        query += " AND appointments.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND appointments.date <= ?"
        params.append(end_date)

    if service:
        query += " AND appointments.service = ?"
        params.append(service)

    if search:
        query += " AND (users.name LIKE ? OR users.surname LIKE ? OR users.phone LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY DATE(appointments.date) DESC, TIME(appointments.time) DESC"

    # Esegui query
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Genera CSV
    import csv
    from io import StringIO
    from flask import make_response

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Username', 'Nome', 'Cognome', 'Telefono', 'Servizio', 'Data', 'Ora'])

    for row in rows:
        writer.writerow(row)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=storico_appuntamenti.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/book_hair', methods=['GET', 'POST'])
def book_hair():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        user_id = session['user_id']
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        barber = request.form['barber']  # Es. "Daniela"

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # Controlla se lo slot è già prenotato dalla parrucchiera
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE date = ? AND time = ? AND barber = ? AND tipo = 'parrucchiera'
        """, (date, time, barber))
        if cursor.fetchone()[0] >= 1:
            conn.close()
            return render_template('book_hair.html', error="Orario già prenotato.")

        # Salva l'appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber, tipo)
            VALUES (?, ?, ?, ?, ?, 'parrucchiera')
        """, (user_id, service, date, time, barber))
        conn.commit()

        # 📧 Invio email di conferma
        try:
            cursor.execute("SELECT name, email, phone FROM users WHERE id = ?", (user_id,))
            user_info = cursor.fetchone()
            if user_info and user_info[1]:
                invia_email_appuntamento(
                    destinatario=user_info[1],
                    nome=user_info[0],
                    telefono=user_info[2],
                    email=user_info[1],
                    servizio=service,
                    data=date,
                    ora=time,
                    barbiere=barber
                )
        except Exception as e:
            print("❌ Errore invio email appuntamento donna:", e)

        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book_hair.html')



@app.route('/admin_book', methods=['GET', 'POST'])
def admin_book():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    date = request.args.get('date')
    time = request.args.get('time')

    if request.method == 'POST':
        name = request.form['name'].strip()
        surname = request.form['surname'].strip()
        phone = request.form['phone'].strip()
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        barber = request.form['barber']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        user = None

        # 🔍 Se il numero è stato inserito, cerca l'utente
        if phone:
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            user = cursor.fetchone()

        # 👤 Se non esiste, crea nuovo utente con username univoco
        if not user:
            base_username = f"{name.lower()}.{surname.lower()}"[:20]
            username = base_username
            suffix = 1

            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            while cursor.fetchone():
                username = f"{base_username}{suffix}"
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                suffix += 1

            cursor.execute("""
                INSERT INTO users (username, password, name, surname, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (username, 'admin-creato', name, surname, phone if phone else "ND"))
            user_id = cursor.lastrowid
        else:
            user_id = user[0]

        # ⛔️ Controllo: massimo 2 appuntamenti nello stesso slot
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ?", (date, time))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template("admin_book.html", date=date, time=time, error="Slot già pieno")

        # ✅ Inserimento appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, barber))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_book.html", date=date, time=time)

if __name__ == '__main__':
    app.run(debug=True)
