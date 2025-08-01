import tinytuya
import time
from threading import Thread
from config import DEVICE_CONFIG

class TuyaDevice:
    def __init__(self):
        self.device = tinytuya.OutletDevice(
            DEVICE_CONFIG['DEVICE_ID'],
            DEVICE_CONFIG['DEVICE_IP'],
            DEVICE_CONFIG['LOCAL_KEY']
        )
        self.device.set_version(DEVICE_CONFIG['VERSION'])
        self._keep_alive_active = True
        self._start_keep_alive()
        self.last_status = {
            'power': 0,
            'voltage': 0,
            'current': 0,
            'connected': False
        }

    def _start_keep_alive(self):
        """Background thread to ping device every 25 seconds"""
        def keep_alive():
            while self._keep_alive_active:
                try:
                    self.device.status()  # Ping device
                    time.sleep(25)  # Slightly less than 30s sleep threshold
                except Exception as e:
                    print(f"Keep-alive error: {e}")
                    time.sleep(10)
        
        Thread(target=keep_alive, daemon=True).start()

    def get_status(self):
        try:
            status = self.device.status()
            dps = status.get('dps', {})
            self.last_status = {
                'power': dps.get('19', 0) / 10,
                'voltage': dps.get('20', 0) / 10,
                'current': dps.get('18', 0) / 1000,
                'connected': True
            }
            return self.last_status
        except Exception as e:
            print(f"Error in get_status: {e}")
            return {'connected': False}

    def turn_on(self):
        result = self._send_command(True)
        return {'status': 'success' if result else 'error',
                'message': 'Turned ON' if result else 'Failed to turn ON'}

    def turn_off(self):
        result = self._send_command(False)
        return {'status': 'success' if result else 'error',
                'message': 'Turned OFF' if result else 'Failed to turn OFF'}

    def _send_command(self, state):
        try:
            self.device.set_status(state)
            return True
        except Exception as e:
            print(f"Command error: {e}")
            return False

    def stop_keep_alive(self):
        self._keep_alive_active = False