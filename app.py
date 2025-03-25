from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Inizializza il database
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
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

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Login admin
@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login_admin.html', error="Invalid admin credentials")
    return render_template('login_admin.html')

# Login user
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
            return render_template('login_user.html', error="Invalid credentials")
    return render_template('login_user.html')

# Registrazione utenti
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error="Username already exists")
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login_user'))
    return render_template('register.html')

# Dashboard utente
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

# Dashboard admin
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login_admin'))
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT appointments.id, users.username, appointments.service, appointments.date, appointments.time 
        FROM appointments 
        JOIN users ON appointments.user_id = users.id
    """)
    appointments = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', appointments=appointments)

# Prenotazione appuntamenti - AGGIORNATA con controllo giorni
@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    if request.method == 'POST':
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']

        # Controllo giorno della settimana
        day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()  # 0 = Monday, 6 = Sunday
        if day_of_week < 1 or day_of_week > 5:  # Consentito solo da martedì (1) a sabato (5)
            return render_template('book.html', error="Le prenotazioni sono consentite solo dal martedì al sabato..")

        conn = sqlite3.connect('bookings.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE date = ? AND time = ?", (date, time))
        existing_appointment = cursor.fetchone()
        if existing_appointment:
            conn.close()
            return render_template('book.html', error="This time slot is already booked. Please choose another time.")

        cursor.execute("INSERT INTO appointments (user_id, service, date, time) VALUES (?, ?, ?, ?)", 
                       (user_id, service, date, time))
        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))

    return render_template('book.html')

@app.route('/get_booked_times', methods=['POST'])
def get_booked_times():
    data = request.get_json()
    date = data.get('date')

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT time FROM appointments WHERE date = ?", (date,))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    return jsonify({'booked_times': booked_times})


# Modifica prenotazione
@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        new_service = request.form['service']
        new_date = request.form['date']
        new_time = request.form['time']
        cursor.execute("UPDATE appointments SET service = ?, date = ?, time = ? WHERE id = ? AND user_id = ?", 
                       (new_service, new_date, new_time, appointment_id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))

    cursor.execute("SELECT id, service, date, time FROM appointments WHERE id = ? AND user_id = ?", 
                   (appointment_id, session['user_id']))
    appointment = cursor.fetchone()
    conn.close()
    if appointment:
        return render_template('edit_appointment.html', appointment=appointment)
    else:
        return redirect(url_for('user_dashboard'))

# Cancellazione prenotazione
@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if 'user_id' not in session and 'admin' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    if 'admin' in session:
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    else:
        cursor.execute("DELETE FROM appointments WHERE id = ? AND user_id = ?", (appointment_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Appointment deleted successfully'})

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

