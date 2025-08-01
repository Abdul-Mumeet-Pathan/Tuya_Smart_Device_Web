from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime, timedelta
import json
import os
import atexit
from tuya_control import TuyaDevice
from config import DATA_FILES

from flask import Flask, jsonify, request
import threading
import time


app = Flask(__name__)
device = TuyaDevice()

# Initialize data files if they don't exist
if not os.path.exists('data'):
    os.makedirs('data')

if not os.path.exists(DATA_FILES['energy_logs']):
    with open(DATA_FILES['energy_logs'], 'w') as f:
        json.dump([], f)

if not os.path.exists(DATA_FILES['device_status']):
    with open(DATA_FILES['device_status'], 'w') as f:
        json.dump({'status': 'unknown'}, f)

# Replace log_energy_data() with:
def log_energy_data():
    """Log only if values changed significantly"""
    data = device.get_status()
    if not data.get('connected'):
        return

    with open(DATA_FILES['energy_logs'], 'r+') as f:
        logs = json.load(f)
        last_log = logs[-1] if logs else None
        
        # Only log if power changed by >1W or 5 minutes passed
        should_log = (
            not last_log or 
            abs(data['power'] - last_log['power']) > 1 or
            (datetime.now() - datetime.strptime(last_log['timestamp'], '%Y-%m-%d %H:%M:%S')).seconds > 120
        )

        if should_log:
            logs.append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'power': round(data['power'], 2),
                'voltage': round(data['voltage'], 1),
                'current': round(data['current'], 3)
            })
            f.seek(0)
            json.dump(logs, f, indent=2)

def get_energy_logs(date=None):
    """Get energy logs, optionally filtered by date"""
    with open(DATA_FILES['energy_logs'], 'r') as f:
        logs = json.load(f)
    
    if date:
        return [log for log in logs if log['timestamp'].startswith(date)]
    return logs

def get_available_dates():
    """Get unique dates with logged data"""
    with open(DATA_FILES['energy_logs'], 'r') as f:
        logs = json.load(f)
    
    dates = set()
    for log in logs:
        date = log['timestamp'].split()[0]
        dates.add(date)
    
    return sorted(dates, reverse=True)[:30]  # Last 30 days

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/history')
def history():
    date = request.args.get('date')
    dates = get_available_dates()
    
    if date:
        logs = get_energy_logs(date)
        times = [log['timestamp'].split()[1][:5] for log in logs]
        powers = [log['power'] for log in logs]
        volts = [log['voltage'] for log in logs]
        currents = [log['current'] for log in logs]
    else:
        logs = []
        times = powers = volts = currents = []
    
    return render_template('history.html', 
                         dates=dates, 
                         selected_date=date,
                         times=times,
                         powers=powers,
                         volts=volts,
                         currents=currents)

@app.route('/api/status')
def get_status():
    try:
        data = device.get_status()
        if data and data.get('connected'):
            log_energy_data()  # Log data each time we check status
            return jsonify({
                'connected': True,
                'status': 'connected',
                'voltage': data.get('voltage', 0),
                'power': data.get('power', 0),
                'current': data.get('current', 0)
            })
        else:
            return jsonify({
                'connected': False,
                'status': 'disconnected',
                'voltage': None,
                'power': None,
                'current': None
            })
    except Exception as e:
        print(f"Error getting device status: {e}")
        return jsonify({
            'connected': False,
            'status': 'error',
            'voltage': None,
            'power': None,
            'current': None
        }), 500

@app.route('/api/turn_on', methods=['POST'])
def turn_on():
    result = device.turn_on()
    return jsonify(result)

@app.route('/api/turn_off', methods=['POST'])
def turn_off():
    result = device.turn_off()
    return jsonify(result)

@app.teardown_appcontext
def shutdown(exception=None):
    device.stop_keep_alive()

@app.route('/api/timer_on', methods=['POST'])
def timer_on():
    data = request.get_json()
    minutes = data.get('minutes', 0)
    delay = minutes * 60

    def turn_on():
        # replace this with your own device ON code
        print("⏰ Timer reached: Turning device ON")
        # device.set_status(True)
        device.turn_on() 

    threading.Timer(delay, turn_on).start()
    return jsonify({"message": f"Timer set: Device will turn ON in {minutes} minute(s) ✅"})


@app.route('/api/timer_off', methods=['POST'])
def timer_off():
    data = request.get_json()
    minutes = data.get('minutes', 0)
    delay = minutes * 60

    def turn_off():
        # replace this with your own device OFF code
        print("⏰ Timer reached: Turning device OFF")
        # device.set_status(False)
        device.turn_off()

    threading.Timer(delay, turn_off).start()
    return jsonify({"message": f"Timer set: Device will turn OFF in {minutes} minute(s) ✅"})


# Register cleanup
atexit.register(shutdown)

if __name__ == '__main__':
    app.run(debug=True)