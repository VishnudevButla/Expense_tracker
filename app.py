from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'your_secret_key'  # Required for sessions and flash messages

# Database connection helper function
def execute_query(query, params=(), fetch=False):
    connection = sqlite3.connect('project.db')
    connection.row_factory = sqlite3.Row  # To return rows as dictionaries
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
        else:
            connection.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        connection.close()
    return result

# Function to create the database and a table
def create_database():
    # Create tables if they don't exist
    execute_query('''
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            pword TEXT NOT NULL
        );
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS data (
            exp_no INTEGER PRIMARY KEY AUTOINCREMENT,
            place TEXT NOT NULL,
            amount REAL NOT NULL,
            exp_date TEXT NOT NULL,
            uid INTEGER NOT NULL,
            FOREIGN KEY (uid) REFERENCES users(uid)
        );
    ''')

# Run the function to create the database
create_database()

@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    else:
        email = request.form.get("email")
        password_input = request.form.get("password")

        if not email:
            flash("Please enter email!")
            return redirect("/")
        if not password_input:
            flash("Please enter password!")
            return redirect("/")

        # Query database for user
        user = execute_query("SELECT uid, pword FROM users WHERE email = ?", (email,), fetch=True)
        if not user:
            flash("User not found. Please check your credentials!")
            return redirect("/")

        # Validate password
        if password_input != user[0]["pword"]:
            flash("Wrong Password.")
            return redirect("/")

        # Store user ID in session
        session["user_id"] = user[0]["uid"]
        return redirect("/main")

@app.route('/main', methods=["GET", "POST"])
def main():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect("/")

    if request.method == 'POST':
        place = request.form.get("place")
        amount = request.form.get("amt")

        if not place:
            flash("Please enter a place")
        elif not amount:
            flash("Please enter an amount")
        else:
            expno = request.form.get("no")
            execute_query(
                "INSERT INTO data (exp_no, place, amount, exp_date, uid) VALUES (?, ?, ?, ?, ?)",
                (expno, place, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session["user_id"])
            )
            flash("Expense added successfully!")

    # Fetch all expenses for the logged-in user
    expenses = execute_query("SELECT * FROM data WHERE uid = ?", (session["user_id"],), fetch=True)
    return render_template("main.html", expenses=expenses)

@app.route('/del', methods=["GET", "POST"])
def delete():
    if request.method == "POST":
        delnum = request.form.get("delno")
        amt = execute_query("SELECT amount FROM data WHERE exp_no = ? AND uid = ?", (delnum, session["user_id"]), fetch=True)

        if amt and amt[0]["amount"] > 0:
            execute_query("DELETE FROM data WHERE exp_no = ? AND uid = ?", (delnum, session["user_id"]))
            flash("Expense deleted successfully!")
        else:
            flash("Expense does not exist")

    expenses = execute_query("SELECT * FROM data WHERE uid = ?", (session["user_id"],), fetch=True)
    return render_template("main.html", expenses=expenses)

@app.route('/total', methods=["GET", "POST"])
def tot():
    expenses = execute_query("SELECT * FROM data WHERE uid = ?", (session["user_id"],), fetch=True)
    total = 0
    today = str(datetime.now().date())

    if request.method == 'POST':
        filter_type = request.form.get("dropdown").strip().lower()

        for expense in expenses:
            exp_date = expense['exp_date'][:10]
            amount = expense['amount']

            if filter_type == 'day' and exp_date == today:
                total += amount
            elif filter_type == 'month' and exp_date[5:7] == today[5:7] and exp_date[:4] == today[:4]:
                total += amount
            elif filter_type == 'year' and exp_date[:4] == today[:4]:
                total += amount

    return render_template("main.html", expenses=expenses, total=total)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        email = request.form.get("email")
        password = request.form.get("password")

        if not email:
            flash("Please enter an email!")
            return render_template("register.html")
        if not password:
            flash("Please enter a password!")
            return render_template("register.html")

        # Insert new user into the database
        try:
            execute_query("INSERT INTO users (email, pword) VALUES (?, ?)", (email, password))
            flash("Registration successful! Please log in.")
            return redirect("/")
        except sqlite3.IntegrityError:
            flash("User already exists or an error occurred.")
            return render_template("register.html")

if __name__ == '__main__':
    app.run(debug=True)
