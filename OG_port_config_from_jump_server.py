""" This scripts configures OG port directly from Jump server"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
# Remove the old NOCC library path if present
sys.path = [p for p in sys.path if "nocc/pylib" not in p]

import pexpect
import pexpect
import subprocess
import getpass

def run_cmd(child, cmd):
    """
    Run a command on Opengear via an existing pexpect SSH session.
    Returns the output.
    """
    child.sendline(cmd)
    child.expect([r"\$", r"#"])  # wait for prompt
    output = child.before.decode(errors="ignore").strip()
    return output


def main():
    ZTP_ip   = input("Enter ZTP Server IP: ").strip()
    opengear_ip  = input("Enter Opengear IP: ").strip()
    opengear_user = input("Enter Opengear username: ").strip()
    opengear_pass = getpass.getpass("Enter Opengear password: ")

    # Start gwsh session to Server B
    child = pexpect.spawn("/usr/local/tools/bin/gwsh {}".format(ZTP_ip))
    child.expect([r"\$", r"#"])   # wait for Server B shell prompt

    # Check ZTP IP
    child.sendline("hostname")
    child.expect([r"\$", r"#"])
    sZTP_hostname = child.before.decode(errors="ignore").strip().split("\n")[-1]
    ZTP_hostname = subprocess.check_output(["gwsh", ZTP_ip, "hostname"], universal_newlines=True).strip()
    print("\n✅ Reached  ZTP Server,  IHostname and IP is: {} ({})\n".format(ZTP_hostname, sZTP_hostname))

    # Check for ZTP server hostname

    # SSH into Opengear
    child.sendline("ssh {}@{}".format(opengear_user, opengear_ip))
    child.expect([r"[Pp]assword:"])
    child.sendline(opengear_pass)
    child.expect([r"\$", r"#"])

    # Check Opengear hostname
    og_hostname = run_cmd(child, "hostname")
    print("✅ Reached Opengear, hostname is: {}\n".format(og_hostname))

    # --- continue with ports logic below...
    # Ask user for ports
    ports = input("Enter port numbers (comma separated): ").split(",")
    ports = [p.strip() for p in ports if p.strip().isdigit()]

    if not ports:
        print("No valid ports entered.")
        return

    # Select speed
    while True:
        speed_choice = input("Select port speed (1 = 115200, 2 = 9600): ").strip()
        if speed_choice == "1":
            port_speed = 115200
            break
        elif speed_choice == "2":
            port_speed = 9600
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # Apply config per port
    for port in ports:
        label = input("Enter label for port {}: ".format(port)).strip()
        if not label:
            label = "Port-{}".format(port)

        commands = [
            "config -s config.ports.port{}.label='{}'".format(port, label),
            "config -s config.ports.port{}.speed={}".format(port, port_speed),
            "config -s config.ports.port{}.parity=None".format(port),
            "config -s config.ports.port{}.charsize=8".format(port),
            "config -s config.ports.port{}.stop=1".format(port),
            "config -s config.ports.port{}.flow=none".format(port),
            "config -s config.ports.port{}.protocol=RS232".format(port),
            "config -s config.ports.port{}.log.level=0".format(port),
            "config -s config.ports.port{}.escapechar='%'".format(port),
            "config -s config.ports.port{}.mode=portmanager".format(port),
        ]

        for cmd in commands:
            result = run_cmd(child, cmd)
            print("Ran: {} -> {}".format(cmd, result))

    # Save config
    result = run_cmd(child, "config -a")
    print("\n✅ Configuration applied and saved -> {}\n".format(result))

if __name__ == "__main__":
    main()

