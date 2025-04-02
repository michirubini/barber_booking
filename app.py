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


@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/delete_all_appointments', methods=['POST'])
def delete_all_appointments():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']

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

@app.route('/admin_book', methods=['GET', 'POST'])
def admin_book():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    date = request.args.get('date')
    time = request.args.get('time')

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()

        if not user:
            username = f"{name.lower()}.{surname.lower()}"[:20]
            cursor.execute("INSERT INTO users (username, password, name, surname, phone) VALUES (?, ?, ?, ?, ?)",
                           (username, 'admin-creato', name, surname, phone))
            user_id = cursor.lastrowid
        else:
            user_id = user[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ? AND time = ?", (date, time))
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return render_template("admin_book.html", date=date, time=time, error="Slot già pieno")

        cursor.execute("INSERT INTO appointments (user_id, service, date, time) VALUES (?, ?, ?, ?)",
                       (user_id, service, date, time))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template("admin_book.html", date=date, time=time)

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
            '12:00','12:30','13:00','13:30','14:00','14:30','15:00'
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
        SELECT appointments.id, users.name, users.phone, appointments.service, appointments.time
        FROM appointments
        JOIN users ON users.id = appointments.user_id
        WHERE appointments.date = ?
    """, (date,))
    records = cursor.fetchall()
    conn.close()

    slots = {t: [] for t in times}
    for appointment_id, name, phone, servizio, time in records:
        if time in slots:
            slots[time].append({
                'id': appointment_id,
                'name': name,
                'phone': phone,
                'servizio': servizio
            })

    return jsonify({'slots': slots})

@app.route('/get_booked_times', methods=['POST'])
def get_booked_times():
    data = request.get_json()
    date = data.get('date')

    if not date:
        return jsonify({'error': 'Data mancante'}), 400

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT time FROM appointments WHERE date = ?", (date,))
    times = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify({'booked_times': times})


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
