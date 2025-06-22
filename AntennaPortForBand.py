import time
import xmlrpc.client
from datetime import datetime

FLRIG_HOST = "192.168.1.31"  # Replace with your flrig host
FLRIG_PORT = 12345           # Default flrig XML-RPC port
server_url = f"http://{FLRIG_HOST}:{FLRIG_PORT}/RPC2"

def determine_antenna_button(frequency_mhz):
    """
    Determine the button number to trigger based on frequency.
    """
    if 1.8 <= frequency_mhz <= 2.0:  # 160m
        return 2  # ANT2 corresponds to User Button #2
    elif 5.3 <= frequency_mhz <= 5.4:  # 60m
        return 2  # ANT2 corresponds to User Button #2
    elif 3.5 <= frequency_mhz <= 54:  # 80m to 6m
        return 1  # ANT1 corresponds to User Button #1
    else:
        return None  # Frequency is out of supported range

def switch_antenna():
    """
    Core logic to determine the frequency and switch antenna ports.
    """
    try:
        # Connect to the flrig server
        client = xmlrpc.client.ServerProxy(server_url)
        print("Connected to flrig")

        # Get current frequency
        frequency_hz = float(client.rig.get_vfoA())
        frequency_mhz = frequency_hz / 1e6
        print(f"Current Frequency (VFO A): {frequency_mhz:.3f} MHz")

        # Determine the correct user-defined button
        button = determine_antenna_button(frequency_mhz)
        if button:
            print(f"Switching antenna using User Button #{button}")
            
            # Trigger the user-defined button via rig.cmd
            response = client.rig.cmd(button)
            print(f"Button #{button} execution response: {response}")

            if response is None:
                print(f"Antenna successfully switched using Button #{button}.")
            else:
                print(f"Unexpected response: {response}")

        else:
            print("Frequency is outside supported range. No action taken.")

    except Exception as e:
        print(f"Error: {e}")

def wait_until_next_minute():
    """
    Wait until exactly :00.750 seconds of the next minute.
    """
    while True:
        now = datetime.now()
        milliseconds = now.microsecond // 1000
        if now.second == 0 and milliseconds >= 750:
            break
        time.sleep(0.001)  # Sleep in small increments to stay accurate

def calculate_sleep_duration():
    """
    Calculate the sleep duration until exactly :00.750 seconds of the next minute.
    """
    now = datetime.now()
    seconds_to_next_minute = 60 - now.second - 1  # Time until the next minute
    # Convert microseconds to seconds and calculate the total sleep time
    sleep_time = seconds_to_next_minute + 0.750 - (now.microsecond / 1_000_000.0)
    return max(0, sleep_time)  # Ensure sleep time is never negative

def main():
    print("Starting Antenna Switching Service...")
    print("Script will run at :00.750 of every minute.")
    
    while True:
        # Calculate sleep duration and ensure it's non-negative
        sleep_time = calculate_sleep_duration()
        print(f"Sleeping for {sleep_time:.3f} seconds until the next :00.750 mark.")
        time.sleep(sleep_time)  # Sleep for the calculated duration
        
        # Run the antenna switch logic
        switch_antenna()

if __name__ == "__main__":
    main()
