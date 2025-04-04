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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Username già esistente")
        cursor.execute("""
            INSERT INTO users (username, password, name, surname, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (username, password, name, surname, phone))
        conn.commit()
        conn.close()
        return redirect(url_for('login_user'))
    return render_template('register.html')

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    user_id = session['user_id']
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, date, time FROM appointments WHERE user_id = ?", (user_id,))
    appointments = cursor.fetchall()
    conn.close()
    return render_template('user_dashboard.html', appointments=appointments)

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
               appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
        WHERE appointments.date >= ?
        ORDER BY DATE(appointments.date), TIME(appointments.time)
    """, (today,))
    appointments = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', appointments=appointments)

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        preferred_barber = request.form.get('barber', '')
        user_id = session['user_id']

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_obj = datetime.strptime(time, "%H:%M").time()
            now = datetime.now()

            # 📅 Blocco date passate
            if date_obj.date() < now.date():
                return render_template('book.html', error="Non puoi prenotare in una data passata.")

            # ⏰ Se oggi, controlla che manchi almeno 1 ora
            if date_obj.date() == now.date():
                appointment_datetime = datetime.combine(date_obj.date(), time_obj)
                if appointment_datetime < now + timedelta(hours=1):
                    return render_template('book.html', error="Devi prenotare almeno un'ora prima.")

            # 📆 Solo martedì-sabato
            weekday = date_obj.weekday()
            if weekday < 1 or weekday > 5:
                return render_template('book.html', error="Prenotabile solo da martedì a sabato.")

            # 🕒 Sabato solo fino alle 15:00
            if weekday == 5 and time > '15:00':
                return render_template('book.html', error="Sabato solo fino alle 15:00.")
        except:
            return render_template('book.html', error="Data o orario non validi.")

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()

        # 🔍 Controlla barbieri già prenotati per quell'orario
        cursor.execute("""
            SELECT barber FROM appointments
            WHERE date = ? AND time = ?
        """, (date, time))
        booked_barbers = [row[0] for row in cursor.fetchall()]

        assigned_barber = None

        # 👤 Se il cliente ha scelto una preferenza
        if preferred_barber:
            if preferred_barber not in booked_barbers:
                assigned_barber = preferred_barber
            else:
                # Assegna l'altro se libero
                other = 'Achille' if preferred_barber == 'Mattia' else 'Mattia'
                if other not in booked_barbers:
                    assigned_barber = other
        else:
            # 🔄 Nessuna preferenza, assegna un barbiere disponibile
            for b in ['Mattia', 'Achille']:
                if b not in booked_barbers:
                    assigned_barber = b
                    break

        if not assigned_barber:
            conn.close()
            return render_template('book.html', error="Orario già pieno.")

        # ✅ Salva appuntamento
        cursor.execute("""
            INSERT INTO appointments (user_id, service, date, time, barber)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, assigned_barber))

        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book.html')

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session and 'admin' not in session:
        return redirect(url_for('login_user'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Recupera anche il barbiere se sei admin
    if 'admin' in session:
        cursor.execute("SELECT id, service, date, time, barber FROM appointments WHERE id = ?", (appointment_id,))
    else:
        cursor.execute("SELECT id, service, date, time, barber FROM appointments WHERE id = ? AND user_id = ?",
                       (appointment_id, session['user_id']))

    appointment = cursor.fetchone()
    if not appointment:
        conn.close()
        return redirect(url_for('admin_dashboard' if 'admin' in session else 'user_dashboard'))

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

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ? AND id != ?",
                       (new_date, new_time, appointment_id))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template("edit_appointment.html", appointment=appointment,
                                   error="Fascia oraria piena.")

        if 'admin' in session:
            new_barber = request.form['barber']
            cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ?, barber = ? WHERE id = ?",
                           (new_service, new_date, new_time, new_barber, appointment_id))
        else:
            cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ? WHERE id = ?",
                           (new_service, new_date, new_time, appointment_id))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard' if 'admin' in session else 'user_dashboard'))

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
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return render_template('account.html', error="Username già in uso.", user=None)

        cursor.execute("""
            UPDATE users SET name = ?, surname = ?, phone = ?, username = ?, password = ?
            WHERE id = ?
        """, (name, surname, phone, username, password, user_id))
        conn.commit()
        conn.close()
        session['username'] = username
        return redirect(url_for('user_dashboard'))

    cursor.execute("SELECT name, surname, phone, username, password FROM users WHERE id = ?", (user_id,))
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
