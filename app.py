from flask import Flask ,render_template, request, redirect, url_for ,flash , session 
from models import db, User, Expense , Income ,Saving
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.security import check_password_hash
from flask import jsonify






app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.secret_key = 'your_secret_key_here'



basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'expenses.db')
 
 

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# db = SQLAlchemy(app)
db.init_app(app)

# Don't import models at the top to avoid circular import
# Do it at the end
from models import User

@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return render_template('home.html', username=None, now=datetime.now)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/motivate', methods=['POST'])
def motivate():
    motivation = request.form.get('motivation')
    # Save to database or session if needed
    flash(f"💬 You wrote: \"{motivation}\" — keep it up!", "success")
    return redirect(url_for('home'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['username'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))  # 👈 This line is important!
        else:
            flash('Invalid credentials. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

   

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Try a different one.')
            return redirect(url_for('register'))

        # Add user to database
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))






@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash("User not found.")
        return redirect(url_for('login'))

    incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
    expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
    savings = Saving.query.filter_by(user_id=user.id).order_by(Saving.date.desc()).all()
    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        amount = float(request.form['amount'])
        description = request.form['description']
        
        new_expense = Expense(
            user_id=user.id,
            date=datetime.strptime(date, "%Y-%m-%d"),
            category=category,
            amount=amount,
            description=description
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added!', 'success')
        return redirect(url_for('dashboard'))

    expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
    total = sum(exp.amount for exp in expenses)
    incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()

    try:
        savings = Saving.query.filter_by(user_id=user.id).order_by(Saving.date.desc()).all()
        total_saved = sum(s.amount for s in savings)
    except Exception as e:
        savings = []
        total_saved = 0.0
        print("Saving model error:", e)


    total_expense = sum(exp.amount for exp in expenses)
    total_income = sum(inc.amount for inc in incomes)
    money_left = total_income - total_expense - total_saved
    savings = Saving.query.filter_by(user_id=user.id).all()
    total_saved = sum(s.amount for s in savings)
    
# After fetching user:
    expenses_by_category = db.session.query(
    Expense.category,
    db.func.sum(Expense.amount)
     ).filter_by(user_id=user.id).group_by(Expense.category).all()

    expense_labels = [row[0] for row in expenses_by_category]
    expense_values = [row[1] for row in expenses_by_category]


    return render_template(
        'dashboard.html',
        username=user.username,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        money_left=money_left,
        total_saved=total_saved,           # ✅ Passed here
        expense_labels=expense_labels,
        expense_values=expense_values
        )

    


@app.route('/income', methods=['GET', 'POST'])
def income():
    if 'username' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        source = request.form['source']

        new_income = Income(
            user_id=user.id,
            date=datetime.strptime(date, "%Y-%m-%d"),
            amount=amount,
            source=source
        )
        db.session.add(new_income)
        db.session.commit()
        flash('Income added!', 'success')
        return redirect(url_for('income'))

    incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
    total_income = sum(i.amount for i in incomes)

    return render_template('income.html', incomes=incomes, total_income=total_income)

@app.route('/savings', methods=['GET', 'POST'])
def savings():
    if 'username' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        goal = request.form['goal']
        note = request.form.get('note', '')
        goal = request.form.get('goal', '')

        new_saving = Saving(
            user_id=user.id,
            date=datetime.strptime(date, "%Y-%m-%d"),
            amount=amount,
            note=note,
            goal=goal
        )

        
        db.session.add(new_saving)
        db.session.commit()
        flash('Saving entry added!', 'success')
        return redirect(url_for('savings'))

    savings = Saving.query.filter_by(user_id=user.id).order_by(Saving.date.desc()).all()
    total_saved = sum(s.amount for s in savings)

    return render_template('savings.html', savings=savings, total_saved=total_saved)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
