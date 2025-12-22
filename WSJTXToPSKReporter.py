import socket
import struct
import time
import os
import re
import argparse
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# Change these to match your station
RECEIVER_CALLSIGN = "N0MQL"
RECEIVER_LOCATOR = "EN35ld"  # e.g., "FN42hn"
SOFTWARE_NAME = "ALL.TXT.ReSendDebug"
SOFTWARE_VERSION = "1.0"

# Path to WSJT-X ALL.TXT on your Linux machine
ALL_TXT_PATH = os.path.expanduser("~/.local/share/WSJT-X/ALL.TXT")

# PSK Reporter UDP settings
PSK_REPORTER_HOST = "report.pskreporter.info"
PSK_REPORTER_PORT = 14739  # Test port is 14739 (packets will be logged but not added to DB). Standard is 4739.
DEBUG_MODE = True        # Set to False for less verbose output

# --- IPFIX CONSTANTS ---
ENTERPRISE_ID = 30351

# Field IDs
FIELD_SENDER_CALLSIGN = 1
FIELD_RECEIVER_CALLSIGN = 2
FIELD_RECEIVER_LOCATOR = 4
FIELD_FREQUENCY = 5
FIELD_SENDER_LOCATOR = 8
FIELD_MODE = 10
FIELD_REPORTING_SOFTWARE = 11
FIELD_REPORTING_SOFTWARE_VERSION = 12
FIELD_FLOW_START_SECONDS = 150

def pack_string(s):
    b = s.encode('ascii')
    if len(b) < 255:
        return struct.pack("B", len(b)) + b
    else:
        return b"\xff" + struct.pack(">H", len(b)) + b

def create_template_packet(sequence_number):
    # This is a simplified IPFIX template packet
    # PSK Reporter expects templates to define the structure of data records
    
    # Header: Version (10), Length, ExportTime, SequenceNumber, ObservationDomainID (0)
    # We'll fill Length later
    
    # Template Set: SetID (2 for Template Set), Length
    # Template Record: TemplateID (256+), FieldCount
    
    # Fields: FieldID, FieldLength (65535 for variable length)
    # If FieldID > 32767, it's Enterprise-specific: FieldID | 0x8000, FieldLength, EnterpriseID
    
    # For simplicity and based on pskdev documentation, we need to report:
    # receiverCallsign, receiverLocator, senderCallsign, senderLocator, frequency, mode, flowStartSeconds
    
    fields = [
        (FIELD_RECEIVER_CALLSIGN | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_RECEIVER_LOCATOR | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_SENDER_CALLSIGN | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_SENDER_LOCATOR | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_FREQUENCY | 0x8000, 4, ENTERPRISE_ID),
        (FIELD_MODE | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_REPORTING_SOFTWARE | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_REPORTING_SOFTWARE_VERSION | 0x8000, 65535, ENTERPRISE_ID),
        (FIELD_FLOW_START_SECONDS, 4, None)
    ]
    
    template_id = 256
    set_id = 2
    
    template_data = struct.pack(">HH", template_id, len(fields))
    for f_id, f_len, ent_id in fields:
        if ent_id:
            template_data += struct.pack(">HH I", f_id, f_len, ent_id)
        else:
            template_data += struct.pack(">HH", f_id, f_len)
            
    set_length = 4 + len(template_data)
    set_header = struct.pack(">HH", set_id, set_length)
    
    export_time = int(time.time())
    header_length = 16
    total_length = header_length + set_length
    
    header = struct.pack(">HHII I", 10, total_length, export_time, sequence_number, 0)
    
    return header + set_header + template_data

def create_data_packet(sequence_number, spots):
    # Header
    # Data Set: SetID (template_id = 256), Length
    
    template_id = 256
    data_records = b""
    
    for spot in spots:
        record = b""
        record += pack_string(RECEIVER_CALLSIGN)
        record += pack_string(RECEIVER_LOCATOR)
        record += pack_string(spot['sender_callsign'])
        record += pack_string(spot['sender_locator'])
        record += struct.pack(">I", int(spot['frequency']))
        record += pack_string(spot['mode'])
        record += pack_string(SOFTWARE_NAME)
        record += pack_string(SOFTWARE_VERSION)
        record += struct.pack(">I", int(spot['timestamp']))
        data_records += record
        
    set_length = 4 + len(data_records)
    set_header = struct.pack(">HH", template_id, set_length)
    
    export_time = int(time.time())
    header_length = 16
    total_length = header_length + set_length
    
    header = struct.pack(">HHII I", 10, total_length, export_time, sequence_number, 0)
    
    return header + set_header + data_records

def parse_all_txt(file_path, minutes_ago=60):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return []

    print(f"Reading {file_path}...")
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    spots = []
    
    # Example lines:
    # 251222_052015  14.074 Rx FT8    -12  0.3 1245 K1ABC FN42
    # 251222_052015  14.074 MHz  FT8  -12  0.8  1245 K1ABC FN42
    
    # More flexible pattern:
    # 1: Timestamp (YYMMDD_HHMMSS)
    # 2: Frequency (MHz)
    # 3: Mode (FT8, FT4, etc)
    # 4: SNR
    # 5: DT
    # 6: Audio Freq
    # 7: Callsign
    # 8: Grid (optional)
    pattern = re.compile(r"^(\d{6}_\d{6})\s+([\d\.]+)\s+(?:MHz\s+)?(?:Rx\s+)?(\S+)\s+(-?\d+)\s+([\d\.]+)\s+(\d+)\s+([A-Z0-9/]+)(?:\s+([A-Z0-9]+))?")

    try:
        with open(file_path, "r") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    dt_str, freq_mhz, mode, snr, dt, sync, call, loc = match.groups()
                    if not loc: loc = "" # Grid might be missing in some decodes
                    try:
                        # WSJT-X log timestamp is UTC in ALL.TXT
                        dt_obj = datetime.strptime(dt_str, "%y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
                        
                        # DEBUG: print(f"Comparing {dt_obj} >= {since}")
                        
                        if dt_obj >= since:
                            spots.append({
                                'timestamp': dt_obj.timestamp(),
                                'frequency': float(freq_mhz) * 1e6,
                                'mode': mode,
                                'sender_callsign': call,
                                'sender_locator': loc
                            })
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading file: {e}")

    print(f"Found {len(spots)} spots in the last {minutes_ago} minutes.")
    return spots

def main():
    parser = argparse.ArgumentParser(description="Send WSJT-X spots from ALL.TXT to PSK Reporter for debugging.")
    parser.add_argument("--reportLimit", type=int, default=0, help="Limit the number of latest spots to send (0 = all).")
    args = parser.parse_args()

    if RECEIVER_CALLSIGN == "REPLACE_ME":
        print("Please configure your CALLSIGN and GRID in the script.")
        return

    spots = parse_all_txt(ALL_TXT_PATH)
    
    if not spots:
        print("No new spots to report.")
        return

    # Apply limit if specified
    if args.reportLimit > 0:
        # spots are added in chronological order, so the latest are at the end
        if len(spots) > args.reportLimit:
            print(f"Limiting to the latest {args.reportLimit} spots.")
            spots = spots[-args.reportLimit:]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sequence_number = int(time.time()) & 0xFFFFFFFF
    
    # 1. Send Template
    if DEBUG_MODE:
        print("\n--- Sending Template Packet ---")
    template_packet = create_template_packet(sequence_number)
    if DEBUG_MODE:
        print(f"Template Packet Length: {len(template_packet)}")
        print(f"Hex: {template_packet.hex()}")
    
    sock.sendto(template_packet, (PSK_REPORTER_HOST, PSK_REPORTER_PORT))
    sequence_number = (sequence_number + 1) & 0xFFFFFFFF
    
    # Small delay to ensure template is processed
    time.sleep(1)
    
    # 2. Send Data
    if DEBUG_MODE:
        print(f"\n--- Sending Data Packets for {len(spots)} spots ---")
    
    for i, spot in enumerate(spots):
        if DEBUG_MODE:
            print(f"\nSpot {i+1}/{len(spots)}: {spot['sender_callsign']} at {spot['frequency']/1e6} MHz ({spot['mode']})")
        
        data_packet = create_data_packet(sequence_number, [spot])
        
        if DEBUG_MODE:
            print(f"Data Packet Length: {len(data_packet)}")
            print(f"Hex: {data_packet.hex()}")
        
        try:
            sock.sendto(data_packet, (PSK_REPORTER_HOST, PSK_REPORTER_PORT))
            if DEBUG_MODE:
                print("Packet sent successfully to UDP socket.")
        except Exception as e:
            print(f"Error sending packet: {e}")
            
        sequence_number = (sequence_number + 1) & 0xFFFFFFFF
        # PSK Reporter recommends a small gap
        time.sleep(0.2) 

    print(f"\nFinished sending {len(spots)} reports.")

if __name__ == "__main__":
    main()
