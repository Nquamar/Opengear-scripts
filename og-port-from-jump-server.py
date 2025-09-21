"""this script take the input as ip from where OG is reachable, OG ip, and port number wana configure and speed for the port. and run from jump server. it prints port details before and after config."""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
# Remove the old NOCC library path if present
sys.path = [p for p in sys.path if "nocc/pylib" not in p]

import re
import pexpect
import subprocess
import getpass
import time
import ipaddress

# regex to remove ANSI escape sequences (covers common CSI, OSC, etc.)
_ansi_re = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')


def validate_ipv4(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.version == 4:
            return True
        else:
            return False
    except ValueError:
        return False




def strip_ansi(text):
    """
    Remove ANSI escape sequences from a bytes or str input and return a str.
    """
    if text is None:
        return ""
    # If bytes -> decode (ignore errors)
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8', errors='ignore')
        except Exception:
            text = text.decode('latin1', errors='ignore')
    return _ansi_re.sub('', text).strip()


def validate_opengear_ip(child, expected_ip):
    """
    Validate that the Opengear's configured IP matches what the user provided.
    """
    output = run_cmd(child, "ip -4 addr show")
    # Extract all IPv4 addresses
    found_ips = re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', output)

    if expected_ip in found_ips:
        print("✅ Opengear IP validation successful: {}".format(expected_ip))
        return True
    else:
        print("❌ ERROR: Opengear IP {} not found in device IPs: {}".format(
            expected_ip, ", ".join(found_ips) if found_ips else "None"
        ))
        return False


def wait_prompt(child, timeout=10, ask_gwsh_pass=True):
    """
    Wait for either a password prompt or a shell prompt ($ or #).
    If gwsh asks for password this function will prompt the user (once) and send it.
    Returns the cleaned text that appeared *before* the matched prompt.
    """
    try:
        # Look for password (case-insensitive) OR shell prompt symbols.
        i = child.expect([r'(?is).*password:', r'\$', r'#'], timeout=timeout)
    except pexpect.TIMEOUT:
        raise
    if i == 0:
        # password prompt matched
        # prompt user for gwsh password (if allowed)
        if ask_gwsh_pass:
            gwsh_pass = getpass.getpass("Enter Open-gear password: ")
        else:
            gwsh_pass = ""   # send empty if not allowed (unlikely)
        child.sendline(gwsh_pass)
        # now wait for the actual shell prompt
        child.expect([r'\$', r'#'], timeout=timeout)
        out = child.before
        return strip_ansi(out)
    else:
        # i == 1 or 2 -> we got a shell prompt
        out = child.before
        return strip_ansi(out)

def run_cmd(child, cmd, timeout=10):
    """
    Run a command on the remote shell (child) and return cleaned output (text before prompt).
    """
    child.sendline(cmd)
    # wait for the prompt; tolerant match for any preceding garbage
    try:
        child.expect([r'(?is).*password:', r'\$', r'#'], timeout=timeout)
    except pexpect.TIMEOUT:
        raise
    # if password prompt unexpectedly showed up (shouldn't for run_cmd), handle and wait again
    last = child.before
    matched = child.match
    # if matched is password, send nothing (we assume authenticated)
    if matched and re.search(r'(?i)password:', matched.group(0).decode('utf-8', errors='ignore') if isinstance(matched.group(0), bytes) else matched.group(0)):
        # This is unexpected during command runs, but handle gracefully:
        gw = getpass.getpass("Password prompt appeared while running command, enter password: ")
        child.sendline(gw)
        child.expect([r'\$', r'#'], timeout=timeout)
        last = child.before
    return strip_ansi(last)



def show_ports_status(child):
    """Run pmshell and print output for the user."""
    print("\n--- Current Port Status (via pmshell) ---\n")
    child.sendline("pmshell")
    try:
        child.expect("Connect to port >", timeout=5)
        output = child.before.decode(errors="ignore").strip()
        print(output)
    except pexpect.TIMEOUT:
        print("Timeout waiting for pmshell startup")
        return

    finally:
        # Exit from pmshell back to shell
        child.sendcontrol('c')

        child.expect([r"\$", r"#"], timeout=3)

    print("\n--- End of Port Status ---\n")





def main():
    ZTP_ip   = input("Enter ZTP Server IP: ").strip()
    if not validate_ipv4(ZTP_ip):
        print("❌ Invalid ZTP IP, must be a valid IPv4 address.")
        return
    opengear_ip  = input("Enter Opengear IP: ").strip()
    if not validate_ipv4(opengear_ip):
        print("❌ Invalid  Opengaer_ip IP, must be a valid IPv4 address.")
        return
    opengear_user = input("Enter Opengear username: ").strip()
    opengear_pass = getpass.getpass("Enter Opengear password: ")

    # Start gwsh session to Server B
    child = pexpect.spawn("/usr/local/tools/bin/gwsh {}".format(ZTP_ip), timeout=60)
    # Optional: uncomment to see raw interaction for debugging
    # child.logfile = sys.stdout

    # initial wait: this handles either immediate shell or password prompt
    try:
        wait_prompt(child, timeout=10)
    except pexpect.TIMEOUT:
        print("Timeout waiting for gwsh connection/prompt. Aborting.")
        return

    # get a clean hostname by running hostname (works reliably)
    child.sendline("hostname")
    try:
        cleaned = wait_prompt(child, timeout=10)
    except pexpect.TIMEOUT:
        print("Timeout waiting for hostname. Aborting.")
        return

    # cleaned is the output before the shell prompt, last non-empty line is hostname
    sZTP_hostname = ""
    for line in cleaned.splitlines():
        line = line.strip()
        if line:
            sZTP_hostname = line  # last non-empty line
    # verify ZTP ip appears somewhere in that hostname/prompt
    if ZTP_ip not in sZTP_hostname:
        print("❌ ZTP is not as expected! (expected IP {} in prompt/hostname)".format(ZTP_ip))
        print("Observed: '{}'".format(sZTP_hostname))
        return
    print("\n✅ Reached Server  ZTP hostname/prompt: {}\n".format(sZTP_hostname))

    # SSH into Opengear (handle host-key prompt & password)
    child.sendline("ssh {}@{}".format(opengear_user, opengear_ip))
    try:
        i = child.expect([r'(?is).*password:', r'Are you sure you want to continue connecting.*', r'\$', r'#'], timeout=10)
    except pexpect.TIMEOUT:
        print("Timeout while trying to ssh to Opengear")
        return

    if i == 1:
        # host key question
        child.sendline("yes")
        child.expect([r'(?is).*password:', r'\$', r'#'], timeout=10)
        i = 0 if 'password' in (child.after.decode(errors='ignore') if isinstance(child.after, bytes) else str(child.after)) else 2

    if i == 0:
        child.sendline(opengear_pass)
        try:
            wait_prompt(child, timeout=10)
        except pexpect.TIMEOUT:
            print("Timeout waiting for Opengear shell after password.")
            return

    # Now we are in Opengear
    og_hostname = run_cmd(child, "hostname")
    print("✅ Reached Opengear, hostname is: {}\n".format(og_hostname.splitlines()[-1] if og_hostname else og_hostname))

    # Validate Opengear IP
    if not validate_opengear_ip(child, opengear_ip):
        print("Aborting: Opengear is not the expected device.")
        return

    # Show ports before config
    show_ports_status(child)


    # --- continue with ports logic below...
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


    # Show ports before config
    show_ports_status(child)


    # Cleanup and exit
    child.sendline("exit")
    child.close(force=True)
    sys.exit(0)


if __name__ == "__main__":
    main()



