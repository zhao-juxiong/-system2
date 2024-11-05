from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
from functools import wraps
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY, 
                  item TEXT NOT NULL, 
                  quantity INTEGER NOT NULL, 
                  price REAL NOT NULL)''')
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username == 'admin' and password == 'admin123':
            session['user_id'] = username
            return jsonify({'message': '登录成功'}), 200
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/page')
@login_required
def order_page():
    return render_template('orders.html')

@app.route('/order', methods=['POST'])
@login_required
def place_order():
    data = request.get_json()
    item = data['item']
    quantity = data['quantity']
    price = data['price']

    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (item, quantity, price) VALUES (?, ?, ?)", 
              (item, quantity, price))
    conn.commit()
    conn.close()

    return jsonify({'message': '订单创建成功！'}), 201

def get_db_connection():
    try:
        conn = sqlite3.connect('restaurant.db')
        return conn
    except Exception as e:
        print(f"数据库连接错误: {str(e)}")
        return None

@app.route('/orders', methods=['GET'])
@login_required
def get_orders():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': '数据库连接失败'}), 500
    
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM orders")
        orders = c.fetchall()
        conn.close()

        orders_list = [
            {
                'id': order[0],
                'item': order[1],
                'quantity': order[2],
                'price': order[3],
                'total_price': order[2] * order[3]
            }
            for order in orders
        ]

        return jsonify({'orders': orders_list}), 200
    finally:
        conn.close()

@app.route('/order/<int:order_id>', methods=['DELETE'])
@login_required
def delete_order(order_id):
    try:
        conn = sqlite3.connect('restaurant.db')
        c = conn.cursor()
        
        # 检查订单是否存在
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': '订单不存在'}), 404
            
        # 删除订单
        c.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': '订单已删除'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f'页面未找到: {request.url}')
    return jsonify({'error': '页面未找到'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'服务器错误: {str(error)}')
    return jsonify({'error': '服务器内部错误'}), 500

@app.route('/health')
def health_check():
    try:
        # 测试数据库连接
        conn = get_db_connection()
        if conn:
            conn.close()
            return jsonify({'status': 'healthy', 'database': 'connected'}), 200
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500
    except Exception as e:
        logger.error(f'健康检查失败: {str(e)}')
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
