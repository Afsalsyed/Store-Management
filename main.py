import datetime
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
app.secret_key = '68a523fef420b44edaacbfa00056d79c'
# *************************************************************************
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(128))
    cash_balance = db.Column(db.Float, default = 1000)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    item_name = db.Column(db.String(128))
    qty = db.Column(db.Integer, default = 0)

class Purchase(db.Model): 
    id = db.Column(db.Integer, primary_key = True)
    timestamp = db.Column(db.DateTime, default = db.func.current_timestamp())
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    qty = db.Column(db.Integer)
    rate = db.Column(db.Float)
    amount = db.Column(db.Float)
    item = db.relationship('Item', backref=db.backref('purchases', lazy=True))

class Sales(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    timestamp = db.Column(db.DateTime, default = db.func.current_timestamp())
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    qty = db.Column(db.Integer)
    rate = db.Column(db.Float)
    amount = db.Column(db.Integer)
    item = db.relationship('Item', backref=db.backref('sales', lazy=True))

# *************************************************************************


@app.route('/add_company/', methods=['POST'])
def add_company():
    data = request.get_json()  # Get data sent with request
    company_name = data.get('company_name')
    cash_balance = data.get('cash_balance', 1000)  # Default to 1000 if not provided

    # Create a new Company instance
    new_company = Company(company_name=company_name, cash_balance=cash_balance)
    
    try:
        # Add to the session and commit
        db.session.add(new_company)
        db.session.commit()
        return jsonify({'message': 'Company added successfully!', 'company_id': new_company.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to add company', 'error': str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def item_view():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        items = Item.query.paginate(page=page, per_page=10)
        return render_template('itempage.html', items=items, company=Company.query.first())

    elif request.method == 'POST':
        if request.form.get('_method') == 'PUT':
            try:
                item_id = request.form['item_id']
                item = Item.query.get(item_id)
                if item:
                    item.item_name = request.form['item_name']
                    db.session.commit()
                    flash("Item updated successfully!", "success")
                else:
                    flash("Item not found", "danger")
            except Exception as e:
                flash("An error occurred: " + str(e), "danger")
            return redirect(url_for('item_view'))

        elif request.form.get('_method') == 'DELETE':
            try:
                item_id = request.form['item_id']
                item = Item.query.get(item_id)
                if item:
                    db.session.delete(item)
                    db.session.commit()
                    flash("Item deleted successfully!", "success")
                else:
                    flash("Item not found", "danger")
            except Exception as e:
                flash("An error occurred: " + str(e), "danger")
            return redirect(url_for('item_view'))

        else:  # Regular POST for adding a new item
            try:
                existing_item = Item.query.filter(Item.item_name.ilike(request.form['item_name'])).first()
                if existing_item:
                    flash("Item already exists", "danger")
                    return redirect(url_for('item_view'))
                item = Item(item_name=request.form['item_name'])
                db.session.add(item)
                db.session.commit()
                flash("Item added successfully!", "success")
            except Exception as e:
                flash("An error occurred: " + str(e), "danger")
            return redirect(url_for('item_view'))


@app.route('/purchase/', methods=['GET', 'POST'])
def purchase_view():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        purchases = Purchase.query.order_by(Purchase.id.desc()).paginate(page=page, per_page=10)
        return render_template('purchasepage.html', purchases=purchases, items=Item.query.all(), company = Company.query.first())
    
    elif request.method == 'POST':
        try:
            qty = int(request.form['qty'])
            rate = float(request.form['rate'])
            amount = qty * rate
            item_id = request.form['item_id']
            company = Company.query.first()

            # Check company balance
            if company.cash_balance < amount:
                flash("Insufficient cash balance", "danger")
                return redirect(url_for('purchase_view'))

            # Fetch the item and update quantity
            item = Item.query.get(item_id)
            if not item:
                return "Item not found", 404
            
            # Update item quantity
            item.qty += qty
            purchase = Purchase(item_id=item_id, qty=qty, rate=rate, amount=amount)
            db.session.add(purchase)
            company.cash_balance -= amount
            db.session.commit()
            flash("Purchase added successfully!", "success")
            return redirect(url_for('purchase_view'))
        
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('purchase_view'))

@app.route('/sales/', methods=['GET', 'POST'])
def sales_view():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        sales = Sales.query.order_by(Sales.id.desc()).paginate(page=page, per_page=10)
        return render_template('salepage.html', sales=sales, items=Item.query.all(), company = Company.query.first())
    
    elif request.method == 'POST':
        try:
            qty = int(request.form['qty'])
            rate = float(request.form['rate'])
            amount = qty * rate
            item_id = request.form['item_id']
            company = Company.query.get(1)

            # Fetch the item and check quantity
            item = Item.query.get(item_id)
            if not item:
                return "Item not found", 404
            if item.qty < qty:
                return "Insufficient item quantity", 400
            
            # Update item quantity and company balance
            item.qty -= qty
            sales = Sales(item_id=item_id, qty=qty, rate=rate, amount=amount)
            db.session.add(sales)
            company.cash_balance += amount
            db.session.commit()

            return redirect(url_for('sales_view'))
        
        except Exception as e:
            return f"Error: {str(e)}", 400

@app.route('/get_max_quantity/<int:item_id>', methods=['GET'])
def get_max_quantity(item_id):
    item = Item.query.get(item_id)  # Replace with your model's name
    purchase = Purchase.query.filter_by(item_id=item_id).order_by(Purchase.id.desc()).first()
    if item and purchase:
        return jsonify({'max_quantity': item.qty, 'bought_at': purchase.rate})  # Replace with actual attribute
    else:
        return jsonify({'max_quantity': 0, 'bought_at': 0}), 404


@app.route('/report/', methods=['GET', 'POST'])
def report_view():

    if request.method == 'POST':
        from_date = request.form.get('from_date') or request.args.get('from_date')
        to_date = request.form.get('to_date') or request.args.get('to_date')

        # Query with pagination
        sales = Sales.query.filter(Sales.timestamp.between(from_date, to_date))\
            .order_by(Sales.timestamp.desc())
        
        purchases = Purchase.query.filter(Purchase.timestamp.between(from_date, to_date))\
            .order_by(Purchase.timestamp.desc())

        # Calculate totals from all records (not just current page)
        all_sales = Sales.query.filter(Sales.timestamp.between(from_date, to_date)).all()
        all_purchases = Purchase.query.filter(Purchase.timestamp.between(from_date, to_date)).all()
        
    else:
        today = datetime.date.today()
        sales = Sales.query.filter(func.date(Sales.timestamp) == today)\
            .order_by(Sales.timestamp.desc())
        
        purchases = Purchase.query.filter(func.date(Purchase.timestamp) == today)\
            .order_by(Purchase.timestamp.desc())

        all_sales = Sales.query.filter(func.date(Sales.timestamp) == today).all()
        all_purchases = Purchase.query.filter(func.date(Purchase.timestamp) == today).all()

    total_sales = sum(sale.amount for sale in all_sales)
    total_purchases = sum(purchase.amount for purchase in all_purchases)
    net_profitability = total_sales - total_purchases

    return render_template('report.html',
                         sales=sales,
                         purchases=purchases,
                         total_sales=total_sales,
                         total_purchases=total_purchases,
                         net_profitability=net_profitability,
                         company=Company.query.first())



#**************************************************************************
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug = True)