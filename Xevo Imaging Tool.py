# XEVO - Android Smartwatch Imaging Tool
# Developed by Scott Strachan

import PySimpleGUI as sg
from ppadb.client import Client as AdbClient
import os
import subprocess
import socket
import threading
import re

# Starts the ADB server if not already started
os.system("adb start-server")

def connect_device(ip_address, port=5555):
    # Setups up connection between the device
    os.system(f"adb connect {ip_address}:{port}")

def read_device_info(device):
    # Reads device info
    brand = device.shell("getprop ro.product.brand").strip()  # Gets the brand from device
    model = device.shell("getprop ro.product.model").strip()  # Gets the model number
    android_version = device.shell("getprop ro.system_ext.build.version.release").strip()  # Gets the android version
    imei = device.shell("service call iphonesubinfo 1 | cut -c 52-66 | tr -d '.[:space:]'").strip()  # Gets the IMEI of device

    # Outputs the device info
    output_text = "Device Brand: " + brand.capitalize() + "\n"
    output_text += "Device Model: " + model + "\n"
    output_text += "Android Version: " + android_version + "\n"
    output_text += "IMEI: " + imei + "\n"

    return output_text

def create_forensic_image(device, progress_bar):
    # Created the image from dm-4 partition. May differ per device
    cmd = ('su -c "dd if=/dev/block/dm-4 | dd of=/sdcard/userdata.img"')
    result = device.shell(cmd)
    progress_bar.update_bar(100)  # Set progress bar to 100% when finished
    return result

def transfer_image_to_pc(device, image_file):
    # Transfers the image to users machine
    remote_path = "/sdcard/userdata.img"
    current_dir = os.path.abspath(os.curdir)
    local_path = os.path.join(current_dir, image_file)
    device.pull(remote_path, local_path)

def validate_ip(ip_address):
    # Validates the IP address entered by the user
    ip_pattern = re.compile(
        r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    )
    if ip_pattern.match(ip_address):
        return True
    return False

def validate_port(port):
    # Validates the port number entered by the user
    try:
        port = int(port)
        if 1 <= port <= 65535:
            return True
    except ValueError:
        pass
    return False
    
def main():
    # Builds the GUI
    sg.theme('SystemDefault 1')

    input_column = [
        [sg.Image('logo_small.png')],
        [sg.HorizontalSeparator()],
        [sg.Text('ADB Connection Details', font='Segoe 10 bold')],
        [sg.Text("Enter the Device IP Address:")],
        [sg.InputText(key="IP_ADDRESS", size=(44))],
        [sg.Text("Enter the Port number (default 5037):")],
        [sg.InputText("5037", key="PORT", size=(44))],
        [sg.HorizontalSeparator()],
        [sg.Button("Connect Device", size=(38, 1))],
        [sg.Button("Read Device Info", size=(38, 1))],
        [sg.Button("Create Forensic Image", size=(38, 1))],
        [sg.Button("Transfer Image to PC", size=(38, 1))],
        [sg.Button("Exit",size=(38, 1))],
        [sg.HorizontalSeparator()],
        [sg.Text("Progress:"), sg.ProgressBar(100, orientation='h', size=(22, 20), key="PROGRESS_BAR")]
    ]

    output_column = [
        [sg.Text("Output:", font='Segoe 10 bold')],
        [sg.Multiline(size=(54, 29), horizontal_scroll=True, key='output')],
        [sg.Text("Created by Scott Strachan 2022-2023")]
    ]

    layout = [
        [sg.Column(input_column), sg.VSeparator(), sg.Column(output_column)]
    ]


    window = sg.Window("Xevo", layout)

    adb_client = AdbClient(host="127.0.0.1", port=5037)
    device = None

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            break

        if event == "Connect Device":
            ip_address = values["IP_ADDRESS"]
            port = values["PORT"]

            # Shows user if the IP address and port number is valid
            if not validate_ip(ip_address):
                window['output'].print("Invalid IP address. Please enter a valid IP address.")
                continue
            if not validate_port(port):
                window['output'].print("Invalid port number. Please enter a valid port number.")
                continue
            
            port = int(port)
            connect_device(ip_address, port)
            devices = adb_client.devices()

            if len(devices) > 0:
                device = devices[0]
                window['output'].print(f"Connected to {device.serial}")
            else:
                window['output'].print("No device found. Please check the IP address and port.")

        if event == "Read Device Info" and device:
            output = read_device_info(device)
            window['output'].print(output)

        if event == "Create Forensic Image" and device:
            progress_bar = window["PROGRESS_BAR"]
            def update_output(output):
                window['output'].print(output)

            def threaded_create_forensic_image(device, progress_bar):
                output = create_forensic_image(device, progress_bar)
                window.write_event_value('-THREAD_DONE-', output)

            threading.Thread(target=threaded_create_forensic_image, args=(device, progress_bar)).start()
            window['output'].print("Creating forensic image. This may take some time...")

        if event == '-THREAD_DONE-':
            output = values[event]
            lines = output.splitlines()
            last_two_lines = "\n".join(lines[-2:])
            update_output(last_two_lines)

        if event == "Transfer Image to PC" and device:
            image_file = "image.img"
            transfer_image_to_pc(device, image_file)
            window['output'].print("Forensic image transferred successfully to your PC.")
        
        if event == '-THREAD_DONE-':
            output = values[event]
            update_output(output)

    window.close()

if __name__ == "__main__":
    main()
