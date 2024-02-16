from flask import Flask, render_template, request
from flask_socketio import SocketIO
import time
from threading import Thread
import socket
import queue
import base64
import cv2
import numpy as np
from data_controller import DataController
data_controller = DataController()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

frame_q = queue.Queue()
runing = True

listen_addr  = '192.168.137.1'
target_addr = '192.168.137.125'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

@app.route('/')
def index():
    return render_template('index.html', data_controller=data_controller)  # Ensure you have this HTML file in the templates directory.

@app.route('/update-active-series', methods=['POST'])
def update_active_series():
    selected_series = request.form.getlist('activeSeries')  # Adjusted for checkbox name attribute
    data_controller.active_series = selected_series  # Simple replacement; adjust as needed
    print("Updated active series:", data_controller.active_series)
    
    return 'OK', 200  # Respond indicating success

if __name__ == '__main__':
    thread = Thread(target=background_task)
    thread.daemon = True
    
    udp_thread = Thread(target=udp_recv, args=(listen_addr, target_addr))
    # udp_thread.daemon = True
   
    try:
        thread.start()
        udp_thread.start()
        socketio.run(app)
    except KeyboardInterrupt:
        print("Server down")
        runing = False
        udp_thread.join()
        thread.join()
    finally:
        sock.close()