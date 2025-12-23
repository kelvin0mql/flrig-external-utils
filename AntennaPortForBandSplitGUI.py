import sys
import time
import threading
import xmlrpc.client
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

FLRIG_HOST = "127.0.0.1"  # Replace with your flrig host
FLRIG_PORT = 12345           # Default flrig XML-RPC port
server_url = f"http://{FLRIG_HOST}:{FLRIG_PORT}/RPC2"

class AntennaSwitchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # Initialize data
        self.current_frequency = "Unknown"
        self.current_antenna_port = "Unknown"
        self.last_poll_timestamp = "Never"  # Renamed from last_change_timestamp
        self.last_antenna_change_timestamp = "Never"  # New data attribute
        self.client = None

        # Initialize flrig connection
        self.initialize_flrig_connection()

        # Start the worker thread for antenna switching
        self.start_worker_thread()

    def init_ui(self):
        """Initializes the GUI layout and widgets."""
        self.setWindowTitle("Antenna Switch Monitor")

        self.frequency_label = QLabel("Current Frequency: Unknown")
        self.antenna_label = QLabel("Current Antenna Port: Unknown")
        self.poll_timestamp_label = QLabel("Last Poll Timestamp: Never")  # Renamed
        self.change_timestamp_label = QLabel("Last Antenna Change Timestamp: Never")  # New GUI row

        layout = QVBoxLayout()
        layout.addWidget(self.frequency_label)
        layout.addWidget(self.antenna_label)
        layout.addWidget(self.poll_timestamp_label)
        layout.addWidget(self.change_timestamp_label)  # Add new label to the layout

        self.setLayout(layout)
        self.resize(400, 200)
        self.show()

    def initialize_flrig_connection(self):
        """Initialize connection to flrig."""
        try:
            self.client = xmlrpc.client.ServerProxy(server_url)
            print("Connected to flrig")
        except Exception as e:
            print(f"Error connecting to flrig: {e}")
            self.client = None


    def get_band_name(self, freq_mhz):
        """Returns the band name for a given frequency in MHz."""
        if 1.8 <= freq_mhz <= 2.0:
            return "160m"
        elif 3.5 <= freq_mhz <= 4.0:
            return "80m"
        elif 5.3 <= freq_mhz <= 5.4:
            return "60m"
        elif 7.0 <= freq_mhz <= 7.3:
            return "40m"
        elif 10.1 <= freq_mhz <= 10.15:
            return "30m"
        elif 14.0 <= freq_mhz <= 14.35:
            return "20m"
        elif 18.068 <= freq_mhz <= 18.168:
            return "17m"
        elif 21.0 <= freq_mhz <= 21.45:
            return "15m"
        elif 24.89 <= freq_mhz <= 24.99:
            return "12m"
        elif 28.0 <= freq_mhz <= 29.7:
            return "10m"
        elif 50.0 <= freq_mhz <= 54.0:
            return "6m"
        return None

    def switch_antenna(self):
        """
        Core logic to determine the frequency and switch antenna ports.
        """
        try:
            if self.client:
                # Polling the current frequency
                frequency_hz = float(self.client.rig.get_vfoA())
                frequency_mhz = frequency_hz / 1e6
                
                band_name = self.get_band_name(frequency_mhz)
                if band_name:
                    self.current_frequency = f"{frequency_mhz:.3f} MHz ({band_name})"
                else:
                    self.current_frequency = f"{frequency_mhz:.3f} MHz"
                
                # Update the poll timestamp
                self.last_poll_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # --- 160m Special Mode (RX on ANT3, TX on ANT2) ---
                if 1.8 <= frequency_mhz <= 2.0:
                    try:
                        # Ensure Split is OFF (Internal radio logic handles RX/TX swap via R3/2)
                        if self.client.rig.get_split() != 0:
                            self.client.rig.set_split(0)
                        
                        if self.current_antenna_port != "ANTR3/2":
                            print(f"Configuring 160m R3/2 mode at {self.current_frequency}")
                            # Trigger User Button #9 (configured as AN03; in flrig)
                            self.client.rig.cmd(9)
                            
                            self.current_antenna_port = "ANTR3/2"
                            self.last_antenna_change_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            self.current_antenna_port = "ANTR3/2"

                    except Exception as e:
                        print(f"Error setting 160m R3/2 mode: {e}")
                        self.current_antenna_port = "Failed"

                # --- 60m Special Logic ---
                elif 5.3 <= frequency_mhz <= 5.4:
                    try:
                        # Ensure Split is OFF
                        if self.client.rig.get_split() != 0:
                            self.client.rig.set_split(0)
                        
                        if self.current_antenna_port != "ANT1":
                            self.client.rig.cmd(1) # ANT1
                            self.client.rig.cmd(6) # 15W
                            self.last_antenna_change_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        self.current_antenna_port = "ANT1"
                    except Exception as e:
                        print(f"Error switching antenna/power (60m): {e}")
                        self.current_antenna_port = "Switch Failed"

                # --- Normal Logic (80m to 6m) ---
                elif 3.5 <= frequency_mhz <= 54:
                    try:
                        # Ensure Split is OFF
                        if self.client.rig.get_split() != 0:
                            self.client.rig.set_split(0)

                        if self.current_antenna_port != "ANT1":
                            self.client.rig.cmd(1) # ANT1
                            self.current_antenna_port = "ANT1"
                            self.last_antenna_change_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                    except Exception as e:
                        print(f"Error switching antenna (Normal): {e}")
                        self.current_antenna_port = "Switch Failed"

                else:
                    # Frequency is out of range
                    self.current_antenna_port = "Out of Range"
            else:
                # flrig is not connected
                self.current_frequency = "Unknown (flrig not connected)"
                self.current_antenna_port = "Unknown (flrig not connected)"
        except Exception as e:
            print(f"Error during antenna switching: {e}")
            self.current_frequency = "Error"
            self.current_antenna_port = "Error"

        # Update the GUI labels with the latest values
        self.update_gui()

    def update_gui(self):
        """Updates the GUI with the latest frequency, antenna port, and timestamps."""
        self.frequency_label.setText(f"Current Frequency: {self.current_frequency}")
        self.antenna_label.setText(f"Current Antenna Port: {self.current_antenna_port}")
        self.poll_timestamp_label.setText(f"Last Poll Timestamp: {self.last_poll_timestamp}")
        self.change_timestamp_label.setText(f"Last Antenna Change Timestamp: {self.last_antenna_change_timestamp}")

    def start_worker_thread(self):
        """Starts the worker thread for the antenna switching loop."""
        threading.Thread(target=self.antenna_switching_loop, daemon=True).start()

    def antenna_switching_loop(self):
        """Loop to switch antennas at :00.5, :15.5, :30.5, and :45.5 seconds."""
        polling_times = [0, 15, 30, 45]  # Target times in seconds after the minute
        while True:
            now = datetime.now()
            current_time = now.second + now.microsecond / 1_000_000.0

            # Find the next target time (including the 0.5s offset)
            # Target times are 0.5, 15.5, 30.5, 45.5
            target_times = [t + 0.5 for t in polling_times]
            
            next_target = next((t for t in target_times if t > current_time), target_times[0])
            
            if next_target > current_time:
                sleep_time = next_target - current_time
            else:
                # Wrap around to the next minute
                sleep_time = 60.0 - current_time + next_target

            time.sleep(sleep_time)
            self.switch_antenna()


def main():
    app = QApplication(sys.argv)
    main_window = AntennaSwitchApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
