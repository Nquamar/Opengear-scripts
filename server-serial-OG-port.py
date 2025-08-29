""" this script can pull server serials connected to opengear ports and print . it needs OG ip, user and password to login"""

import paramiko
import pexpect
import getpass
import time


def parse_ports(ports_input):
    ports = []
    for part in ports_input.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            ports.extend(range(int(start), int(end) + 1))
        elif part.isdigit():
            ports.append(int(part))
    return ports


def automate_opengear():
    host = input("Enter Opengear IP: ").strip()
    user = input("Enter Opengear username: ").strip()
    password = getpass.getpass("Enter Opengear password: ")

    # --- Step 2: Connect via SSH and check device hostname ---
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password, timeout=10)

        stdin, stdout, stderr = ssh.exec_command("hostname")
        device_hostname = stdout.read().decode().strip()
        print(f"?~Z| ?~O Opengear reports hostname: {device_hostname}")

    except Exception as e:
        print(f"?~]~L SSH connection failed: {e}")
        return

    # Start SSH session
    ssh_cmd = f"ssh {user}@{host}"
    child = pexpect.spawn(ssh_cmd, encoding='utf-8')

    # Handle Opengear login
    i = child.expect([r"[Pp]assword:", r"yes/no", r"\$|#",
                     pexpect.EOF, pexpect.TIMEOUT])
    if i == 1:
        child.sendline("yes")
        child.expect(r"[Pp]assword:")
        child.sendline(password)
    elif i == 0:
        child.sendline(password)
    child.expect(r"\$|#")

    # ask user port range

    # Example usage
    ports_input = input(
        "Enter port range (e.g. 6-27 or 6-10,15,20-22): ").strip()
    ports = parse_ports(ports_input)

    print("Parsed ports:", ports)

    # -------- Commands to run --------
    commands = [
        "cat /sys/class/dmi/id/product_serial"
    ]

    for port in ports:
        print(f"\n========== Serial of server on port {port} ==========")

        # Enter pmshell
        child.sendline("pmshell")
        child.expect("Port")

        # Select port
        child.sendline(str(port))
        child.sendline("")   # Enter 1
        time.sleep(0.5)

        # Wait until we land on the device shell
        try:
            i = child.expect([r'root@.*[#$]', pexpect.TIMEOUT
                              ], timeout=10)

            if i in [0]:
                # ?~\~E Port responded ?~F~R run your commands

                all_output = []
                for cmd in commands:
                    child.sendline(cmd)
                    time.sleep(2)

                    # Expect the next device prompt
                    child.expect(r'root@.*[#$]')
                    raw_output = child.before.strip()

                    # Add command + result exactly as seen
                    all_output.append(raw_output)

                # Print everything we collected
                print("\n".join(all_output))

            else:
                print(f"?~Z| ?~O Port {port} did not respond, skipping?~@?")

        except pexpect.TIMEOUT:
            print(f"?~O? Timeout on port {port}, skipping?~@?")

        # Logout sequence (% .)
        child.send("%")
        time.sleep(0.2)
        child.send(".")
        time.sleep(1)

        # Back at Opengear shell
        child.expect(r"\$|#")

    print("?~\~E Serial printed for all ports.")


if __name__ == "__main__":
    automate_opengear()
