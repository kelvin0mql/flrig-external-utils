import sys
import time
import threading
import xmlrpc.client
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


FLRIG_HOST = "192.168.1.31"  # Replace with your flrig host
FLRIG_PORT = 12345           # Default flrig XML-RPC port
server_url = f"http://{FLRIG_HOST}:{FLRIG_PORT}/RPC2"


class AntennaSwitchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # Initialize data
        self.current_frequency = "Unknown"
        self.current_antenna_port = "Unknown"
        self.last_change_timestamp = "Never"
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
        self.timestamp_label = QLabel("Last Change Timestamp: Never")

        layout = QVBoxLayout()
        layout.addWidget(self.frequency_label)
        layout.addWidget(self.antenna_label)
        layout.addWidget(self.timestamp_label)

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

    def determine_antenna_button(self, frequency_mhz):
        """
        Determine the button number to trigger based on frequency.
        """
        if 1.8 <= frequency_mhz <= 2.0:  # 160m
            return "ANT2", 2  # ANT2 corresponds to User Button #2
        elif 5.3 <= frequency_mhz <= 5.4:  # 60m
            return "ANT2", 2  # ANT2 corresponds to User Button #2
        elif 3.5 <= frequency_mhz <= 54:  # 80m to 6m
            return "ANT1", 1  # ANT1 corresponds to User Button #1
        else:
            return None, None  # Frequency is out of supported range

    def switch_antenna(self):
        """
        Core logic to determine the frequency and switch antenna ports.
        """
        try:
            # Get the current frequency from flrig
            if self.client:
                frequency_hz = float(self.client.rig.get_vfoA())
                frequency_mhz = frequency_hz / 1e6
                self.current_frequency = f"{frequency_mhz:.3f} MHz"

                # Determine the correct antenna and button
                antenna, button = self.determine_antenna_button(frequency_mhz)
                if antenna and button:
                    # Set GUI variables before switching
                    self.current_antenna_port = antenna  # Assume switch will succeed
                    self.last_change_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Trigger the switch via flrig
                    try:
                        response = self.client.rig.cmd(button)
                        if response is not None:  # Add defensive check for unexpected response
                            print(f"Unexpected response: {response}")
                    except Exception as e:
                        print(f"Error switching antenna: {e}")
                        self.current_antenna_port = "Switch Failed"
                else:
                    # Frequency is out of range for antenna switching
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
        """Updates the GUI with the latest frequency, antenna port, and timestamp."""
        self.frequency_label.setText(f"Current Frequency: {self.current_frequency}")
        self.antenna_label.setText(f"Current Antenna Port: {self.current_antenna_port}")
        self.timestamp_label.setText(f"Last Change Timestamp: {self.last_change_timestamp}")

    def start_worker_thread(self):
        """Starts the worker thread for the antenna switching loop."""
        threading.Thread(target=self.antenna_switching_loop, daemon=True).start()

    def antenna_switching_loop(self):
        """Loop to switch antennas precisely every minute at :00.750 seconds."""
        while True:
            # Calculate sleep duration until the next :00.750 mark
            now = datetime.now()
            seconds_to_next_minute = 60 - now.second - 1
            sleep_time = seconds_to_next_minute + 0.750 - (now.microsecond / 1_000_000.0)
            time.sleep(max(0, sleep_time))  # Ensure sleep time is never negative

            # Perform the antenna switching
            self.switch_antenna()


def main():
    app = QApplication(sys.argv)
    main_window = AntennaSwitchApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
