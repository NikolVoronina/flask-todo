"""
Enkel to-do app med Flask + MariaDB. Les readme.md før du begynner.
Dette scriptet leser DB-innstillinger fra .env
"""

from flask import Flask, render_template, request, redirect
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Last .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "todo_user")
DB_PASS = os.getenv("DB_PASS", "mypassword")
DB_NAME = os.getenv("DB_NAME", "todo")
DB_PORT = int(os.getenv("DB_PORT", 3306))

app = Flask(__name__)

# Funksjon for å koble til MariaDB (leser fra miljøvariabler)
def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT
    )

# Lag tabellen hvis den ikke finnes
def create_table():
    try:
        conn = get_connection()
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    task VARCHAR(255) NOT NULL,
                    completed TINYINT(1) DEFAULT 0
                )
            ''')
            conn.commit()
            cursor.close()
            conn.close()
    except Error as e:
        print(f"Feil under opprettelse av tabell: {e}")

create_table()

@app.route('/')
def index():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks ORDER BY task ASC')
        tasks = cursor.fetchall()
        conn.close()
        return render_template('index.html', tasks=tasks)
    except Error as e:
        # For debug kan du printe e, men i produksjon bør du logge det
        print("DB-tilkoblingsfeil:", e)
        return "Kunne ikke koble til databasen."

@app.route('/add', methods=['POST'])
def add_task():
    task = request.form['task']
    if not task or task.strip() == "":
        return redirect('/')  # enkel validering
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tasks (task) VALUES (%s)', (task.strip(),))
        conn.commit()
    except Error as e:
        print(f"Feil under lagring av oppgave: {e}")
    finally:
        conn.close()
    return redirect('/')

# Nytt: slette en oppgave
@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id=%s', (task_id,))
        conn.commit()
    except Error as e:
        print(f"Feil ved sletting av oppgave: {e}")
    finally:
        conn.close()
    return redirect('/')

# Toggle completed (fra forrige implementasjon)
@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT completed FROM tasks WHERE id=%s', (task_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            return redirect('/')
        current = row[0]
        new_status = 0 if current else 1
        cursor.execute('UPDATE tasks SET completed=%s WHERE id=%s', (new_status, task_id))
        conn.commit()
    except Error as e:
        print(f"Feil under oppdatering av oppgave: {e}")
    finally:
        conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
