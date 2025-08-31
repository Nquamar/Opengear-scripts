"""This script config the OG port user need to share OG ip, passwor, user and port speed"""

  
#!/usr/bin/env python3
import paramiko
import socket
import getpass

def main():
    # Ask user for input  
  
    opengear_ip = input("Enter Opengear IP: ").strip()
    username = input("Enter Opengear username: ").strip()
    password = getpass.getpass("Enter Opengear password: ")

    # --- Step 2: Connect via SSH and check device hostname ---
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(opengear_ip, username=username, password=password, timeout=10)

        stdin, stdout, stderr = ssh.exec_command("hostname")
        device_hostname = stdout.read().decode().strip()
        print(f"?~\~E Opengear reports hostname: {device_hostname}")

    except Exception as e:
        print(f"?~]~L SSH connection failed: {e}")
        return

    # --- Ask which ports to configure ---
    ports = input("Enter port numbers (comma separated): ").split(",")
    ports = [p.strip() for p in ports if p.strip().isdigit()]

    if not ports:
        print("?~]~L No valid port numbers entered.")
        return

    # --- Ask for speed option ---
    while True:
        speed_choice = input("Select port speed (1 = 115200, 2 = 9600): ").strip()
        if speed_choice == "1":
            port_speed = 115200
            break
        elif speed_choice == "2":
            port_speed = 9600
            break
        else:
            print("?~Z| ?~O Invalid choice. Please enter 1 or 2.")

    # --- Collect labels for ports ---
    port_map = {}
    for port in ports:
        label = input(f"Enter label for port {port}: ").strip()
        if not label:
            label = f"Port-{port}"  # fallback label
        port_map[port] = label

    # --- Run configuration commands ---
    for port in ports:
        label = port_map[port]
        commands = [
            f"config -s config.ports.port{port}.label='{label}'",
            f"config -s config.ports.port{port}.speed={port_speed}",   # user-selected speed
            f"config -s config.ports.port{port}.parity=None",
            f"config -s config.ports.port{port}.charsize=8",
            f"config -s config.ports.port{port}.stop=1",
            f"config -s config.ports.port{port}.flow=none",
            f"config -s config.ports.port{port}.protocol=RS232",
            f"config -s config.ports.port{port}.log.level=0",
            f"config -s config.ports.port{port}.escapechar='%'",
            f"config -s config.ports.port{port}.mode=portmanager"
        ]

        print(f"\n?~Z~Y?~O Configuring port {port} on {device_hostname}...\n")
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            err = stderr.read().decode().strip()
            if err:
                print(f"  ?~]~L Error: {err}")
            else:
                print(f"  ?~\~E Ran: {cmd}")

    ssh.exec_command("config -a")
    print("\n?~_~R? Config applied and saved.")
    ssh.close()

if __name__ == "__main__":
    main()
