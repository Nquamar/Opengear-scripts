####################################### Developed by Nurul Quamar ######################################

"""this scripe takes Open Gear IP, User name and password from user. Than logins and verify the hostname.
Give a chance to user if changes are going to be on desired opengear. than ask use port number which can 
be give comma separate. labe for each port. Once everything provided this script will login to open gear
can configure the ports"""



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
        print(f"?~_~V??~O Opengear reports hostname: {device_hostname}")

    except Exception as e:
        print(f"?~]~L SSH connection failed: {e}")
        return

    # --- Ask which ports to configure ---
    ports = input("Enter port numbers (comma separated): ").split(",")
    ports = [p.strip() for p in ports if p.strip().isdigit()]
    ports = [p.strip() for p in ports if p.strip().isdigit()]

    if not ports:
        print("?~]~L No valid port numbers entered.")
    else:
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
            f"config -s config.ports.port{port}.speed=115200",
            f"config -s config.ports.port{port}.parity=None",
            f"config -s config.ports.port{port}.charsize=8",
            f"config -s config.ports.port{port}.stop=1",
            f"config -s config.ports.port{port}.flow=none",
            f"config -s config.ports.port{port}.protocol=RS232",
            f"config -s config.ports.port{port}.log.level=0",
            f"config -s config.ports.port{port}.escapechar='%'",
            f"config -s config.ports.port{port}.mode=portmanager"
        ]

        print(f"\n?~_~T? Configuring port {port} on {device_hostname}...\n")
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            err = stderr.read().decode().strip()
            if err:
                print(f"  ?~Z| ?~O Error: {err}")
            else:
                print(f"  ?~\~E Ran: {cmd}")

    ssh.exec_command("config -a")
    print("\n?~\~E Config applied and saved.")
    ssh.close()

if __name__ == "__main__":
    main()
