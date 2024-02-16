from flask import Flask, render_template, request, jsonify, session,  redirect, url_for, g, flash
from flask import get_flashed_messages
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
import socket
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash
import time
import random
from threading import Thread
from queue import Queue, Empty
import socket
import queue
import base64
import cv2
import numpy as np
from data_controller import DataController
data_controller = DataController()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app)
db = SQLAlchemy(app)
cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
frame_q = queue.Queue()
runing = True

listen_addr  = '192.168.137.1'
target_addr = '192.168.137.125'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

MAX_QUEUE_SIZE = 100 
data_queues = {series_id: Queue(maxsize=MAX_QUEUE_SIZE) for series_id in data_controller.data_series}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    bio = db.Column(db.Text)

    def __repr__(self):
        return '<User %r>' % self.username

@socketio.on('connect')
def handle_connect():
    print('Client connected')

def udp_recv(listen_addr, target_addr):
    try:
        sock.settimeout(1)
        sock.bind((listen_addr, 55556))
    except:
        print("streaming failed")
        return

    # rcvbuf = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)  # 受信バッファサイズの取得
    # print(rcvbuf)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2*16)

    print('Start Streaming...')

    chunks = b''
    try:
        while runing:
            try:
                msg, address = sock.recvfrom(2**16)
            except Exception as e:
                # print('sock.recvfrom',e)
                # sock.sendto(b'\x55', (target_addr, 55555))
                continue
            soi = msg.find(b'\xff\xd8\xff')
            eoi = msg.rfind(b'\xff\xd9')
            # print(time.perf_counter(), len(msg), soi, eoi, msg[:2], msg[-2:])
            if soi >= 0:
                if chunks.startswith(b'\xff\xd8\xff'):
                    if eoi >= 0:
                        chunks += msg[:eoi+2]
                        # print(time.perf_counter(), "Complete picture")
                        eoi = -1
                    else:
                        chunks += msg[:soi]
                        # print(time.perf_counter(), "Incomplete picture")
                    try:
                        frame_q.put(chunks, timeout=1)
                    except Exception as e:
                        print(e)
                chunks = msg[soi:]
            else:
                chunks += msg
            if eoi >= 0:
                eob = len(chunks) - len(msg) + eoi + 2
                if chunks.startswith(b'\xff\xd8\xff'):
                    byte_frame = chunks[:eob]
                    # print(time.perf_counter(), "Complete picture")
                    try:
                        frame_q.put(byte_frame, timeout=1)
                    except Exception as e:
                        print(e)
                else:
                    print(time.perf_counter(), "Invalid picture")
                chunks = chunks[eob:]
    except KeyboardInterrupt:
        sock.close()
        print('Stop Streaming')

def background_task():
    """Example of how to send server generated events to clients."""
    while runing:
        # time.sleep(1)
        # socketio.emit('stream', {'data': 'Let\'s dance'})
        try:
            byte_frame = frame_q.get(block=True, timeout=1)
            frame = cv2.imdecode(np.frombuffer(byte_frame, dtype=np.uint8), cv2.IMREAD_COLOR)
            _, buffer = cv2.imencode('.jpg', frame)

            encoded_string = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('stream', {'data': encoded_string})
            # socketio.emit('stream', {'data': 'Let\'s dance'})
            # print(encoded_string)
        except queue.Empty:
            socketio.emit('stream', {'data': 'Empty'})
            continue

def generate_data_for_series(series_id):
    data_point = {'x': time.time(), 'y': random.randint(1, 100)}
    if series_id in data_queues:
        queue = data_queues[series_id]
        if queue.full():
            try:
                queue.get_nowait() 
            except Empty:
                pass
        queue.put_nowait(data_point)

def data_upstream_receive():
    while True:  # Assuming this runs in a continuous loop or background thread
        with data_controller.lock:  # Ensure thread-safe access to active_series
            active_series = list(data_controller.active_series)  # Make a copy to minimize lock holding time
        
        for series in active_series:
            generate_data_for_series(series)
        
        time.sleep(0.1)  # Adjust the sleep time as needed

def emit_data_task():
    while True:
        for series, queue in data_queues.items():
            # Prepare a list to hold all data points for this emission cycle
            data_points = []
            try:
                while True:  # Keep trying to dequeue until the queue is empty
                    data_point = queue.get_nowait()  # Attempt to dequeue a data point
                    data_points.append(data_point)  # Add the data point to the list
            except Empty:
                pass 
            if data_points:
                socketio.emit('update_data', {'plot_id': series, 'data': data_points})
        time.sleep(0.1)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        # if user is None or not check_password_hash(user.password, password):
        if user.password != password:
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        session.clear()
        session['user_id'] = user.id
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    else:
        return render_template('index.html', data_controller=data_controller)

@app.route('/update-active-series', methods=['POST'])
def update_active_series():
    selected_series = request.form.getlist('activeSeries')  # Adjusted for checkbox name attribute
    with data_controller.lock:
        data_controller.active_series = selected_series  # Simple replacement; adjust as needed
        # print("Updated active series:", data_controller.active_series)
        return jsonify({'active_series': data_controller.active_series}), 200

@app.route('/send-command', methods=['POST'])
def send_command():
    command = request.form['command']
    byte_command = command.encode('utf-8')
    try:
        cli.sendall(byte_command)
    except: 
        pass
    return redirect(url_for('index'))

if __name__ == '__main__':
    thread = Thread(target=background_task)
    thread.daemon = True
    
    udp_thread = Thread(target=udp_recv, args=(listen_addr, target_addr))
    # udp_thread.daemon = True
    data_rec_thread = Thread(target=data_upstream_receive)
    data_send_thread = Thread(target=emit_data_task)

    server_ip = '192.168.137.87'
    server_port = 2022

    print("Creating TCP client socket...")
    cli.settimeout(2)
    print(f"Connecting to server at {server_ip}:{server_port}...")
    cli.connect((server_ip, server_port))
    print("Connection successful.")
   
    try:
        thread.start()
        udp_thread.start()
        data_rec_thread.start()
        data_send_thread.start()
        socketio.run(app)
    except KeyboardInterrupt:
        print("Server down")
        runing = False
        udp_thread.join()
        thread.join()
        data_rec_thread.join()
        data_send_thread.join()
    finally:
        sock.close()
        cli.close()
        print("Socket closed.")