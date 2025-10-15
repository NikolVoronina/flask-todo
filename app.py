"""
Enkel to-do app med Flask + MariaDB. Les readme.md før du begynner.
Dette scriptet leser DB-innstillinger fra .env
"""

from flask import Flask, render_template, request, redirect, flash, url_for
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
SECRET_KEY = os.getenv("SECRET_KEY", "devsecretkey")  # положи SECRET_KEY в .env для продакшна

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Funksjon for å koble til MariaDB (leser fra miljøvariabler)
def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT
    )

# Lag tabellen hvis den ikke finnes (рекомендуется иметь category и created_at)
def create_table():
    try:
        conn = get_connection()
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    task VARCHAR(255) NOT NULL,
                    completed TINYINT(1) DEFAULT 0,
                    category VARCHAR(100) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        category_filter = request.args.get('category', None)

        # Явно указываем колонки — чтобы индексы были предсказуемы
        if category_filter:
            cursor.execute('SELECT id, task, completed, category, created_at FROM tasks WHERE category = %s ORDER BY task ASC', (category_filter,))
        else:
            cursor.execute('SELECT id, task, completed, category, created_at FROM tasks ORDER BY task ASC')

        rows = cursor.fetchall()
        tasks = []
        for row in rows:
            # row: (id, task, completed, category, created_at)
            tasks.append({
                'id': row[0],
                'text': row[1],
                'completed': row[2],
                'category': row[3],
                'created_at': row[4] if len(row) > 4 else None
            })

        cursor.close()
        conn.close()
        return render_template('index.html', tasks=tasks, selected_category=category_filter)

    except Error as e:
        print("Feil ved henting av oppgaver:", e)
        flash("Kunne ikke koble til databasen.", "error")
        return render_template('index.html', tasks=[], selected_category=None)

@app.route('/add', methods=['POST'])
def add_task():
    raw_task = request.form.get('task', '')
    category = request.form.get('category', None)
    task = raw_task.strip()

    # Серверная валидация
    if not task:
        flash("Oppgave kan ikke være tom.", "warning")
        return redirect(url_for('index'))
    if len(task) > 255:
        flash("Oppgave for lang (max 255 tegn).", "warning")
        return redirect(url_for('index'))

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tasks (task, category) VALUES (%s, %s)', (task, category))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Oppgave lagt til!", "success")
    except Error as e:
        print(f"Feil under lagring av oppgave: {e}")
        flash("Feil ved lagring av oppgave.", "error")
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id=%s', (task_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Oppgave slettet.", "success")
    except Error as e:
        print(f"Feil ved sletting av oppgave: {e}")
        flash("Feil ved sletting.", "error")
    return redirect(url_for('index'))

@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT completed FROM tasks WHERE id=%s', (task_id,))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            conn.close()
            flash("Oppgave ikke funnet.", "warning")
            return redirect(url_for('index'))
        current = row[0]
        new_status = 0 if current else 1
        cursor.execute('UPDATE tasks SET completed=%s WHERE id=%s', (new_status, task_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Status oppdatert.", "success")
    except Error as e:
        print(f"Feil under oppdatering av oppgave: {e}")
        flash("Feil ved oppdatering.", "error")
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if request.method == 'GET':
            cursor.execute('SELECT id, task, completed, category FROM tasks WHERE id=%s', (task_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row is None:
                flash("Oppgave ikke funnet.", "warning")
                return redirect(url_for('index'))
            task_obj = {
                'id': row[0],
                'task': row[1],
                'completed': row[2],
                'category': row[3]
            }
            return render_template('edit.html', task=task_obj)

        # POST
        new_text = request.form.get('task', '').strip()
        if not new_text:
            flash("Oppgave kan ikke være tom.", "warning")
            return redirect(url_for('edit_task', task_id=task_id))
        if len(new_text) > 255:
            flash("Oppgave for lang (max 255 tegn).", "warning")
            return redirect(url_for('edit_task', task_id=task_id))

        cursor.execute('UPDATE tasks SET task=%s WHERE id=%s', (new_text, task_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Oppgave oppdatert.", "success")
        return redirect(url_for('index'))

    except Error as e:
        print("Feil ved edit_task:", e)
        flash("Feil ved redigering av oppgave.", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
