from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'

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

@app.route('/')
def index():
    return render_template('index.html')

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
    cursor.execute("DELETE FROM appointments WHERE date < ?", (today,))
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
        user_id = session['user_id']

        try:
            tz_offset = timedelta(hours=1)
            date_obj = datetime.strptime(date, "%Y-%m-%d") + tz_offset
            weekday = date_obj.weekday()

            if weekday < 1 or weekday > 5:
                return render_template('book.html', error="È possibile prenotare solo dal martedì al sabato.")
            if weekday == 5 and time > '15:00':
                return render_template('book.html', error="Il sabato è possibile prenotare solo fino alle 15:00.")
        except Exception:
            return render_template('book.html', error="Data non valida.")

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ?", (date, time))
        count = cursor.fetchone()[0]
        if count >= 2:
            conn.close()
            return render_template('book.html', error="Fascia oraria già piena. Scegli un altro orario.")

        cursor.execute("INSERT INTO appointments (user_id, service, date, time) VALUES (?, ?, ?, ?)",
                       (user_id, service, date, time))
        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book.html')

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, date, time FROM appointments WHERE id = ? AND user_id = ?",
                   (appointment_id, session['user_id']))
    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return redirect(url_for('user_dashboard'))

    appointment_datetime = datetime.strptime(f"{appointment[2]} {appointment[3]}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    if now > appointment_datetime - timedelta(hours=1):
        conn.close()
        return render_template("edit_appointment.html", appointment=appointment,
                               error="Non puoi modificare l'appuntamento meno di un'ora prima.")

    if request.method == 'POST':
        new_service = request.form['service']
        new_date = request.form['date']
        new_time = request.form['time']
        cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ? WHERE id = ? AND user_id = ?",
                       (new_service, new_date, new_time, appointment_id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))

    conn.close()
    return render_template('edit_appointment.html', appointment=appointment)

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if 'user_id' not in session and 'admin' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, time FROM appointments WHERE id = ?", (appointment_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'success': False, 'message': 'Appuntamento non trovato'}), 404

    date_str, time_str = result
    appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()

    if 'user_id' in session and now > appointment_datetime - timedelta(hours=1):
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Non puoi cancellare un appuntamento meno di un’ora prima.'
        }), 403

    if 'admin' in session:
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    else:
        cursor.execute("DELETE FROM appointments WHERE id = ? AND user_id = ?", (appointment_id, session['user_id']))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Appuntamento eliminato'})

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
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT time, COUNT(*) FROM appointments WHERE date = ? GROUP BY time", (date,))
    time_counts = cursor.fetchall()
    conn.close()
    fully_booked = [row[0] for row in time_counts if row[1] >= 2]
    return jsonify({'booked_times': fully_booked})

@app.route('/admin_edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def admin_edit_appointment(appointment_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, date, time FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        new_service = request.form['service']
        new_date = request.form['date']
        new_time = request.form['time']
        cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ? WHERE id = ?",
                       (new_service, new_date, new_time, appointment_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('edit_appointment.html', appointment=appointment)


@app.route('/admin_get_day_slots', methods=['POST'])
def admin_get_day_slots():
    if 'admin' not in session:
        return jsonify({'error': 'Non autorizzato'}), 403

    data = request.get_json()
    date = data.get('date')

    if not date:
        return jsonify({'error': 'Data mancante'}), 400

    try:
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    except ValueError:
        return jsonify({'error': 'Formato data non valido'}), 400

    if weekday == 5:
        times = [
            '09:00','09:30','10:00','10:30','11:00','11:30',
            '12:00','12:30','13:00','13:30','14:00','14:30',
            '15:00'
        ]
    else:
        times = [
            '09:00','09:30','10:00','10:30','11:00','11:30',
            '12:00','12:30','13:00','13:30','14:00','14:30',
            '15:00','15:30','16:00','16:30','17:00','17:30',
            '18:00','18:30','19:00'
        ]

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.name, users.phone, appointments.service, appointments.time
        FROM appointments
        JOIN users ON users.id = appointments.user_id
        WHERE appointments.date = ?
    """, (date,))
    records = cursor.fetchall()
    conn.close()

    slots = {t: [] for t in times}

    for name, phone, servizio, time in records:
        if time in slots:
            slots[time].append({
                'name': name,
                'phone': phone,
                'servizio': servizio
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
            UPDATE users
            SET name = ?, surname = ?, phone = ?, username = ?, password = ?
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
