# written by Nurul Quamar
"""This script can login to all the switches and run the commands and give output. Based on that we can find the switch condition. User have to provide OG ip,
OG user, OG password and switch user and password."""

import pexpect
import getpass
import time
import re

PROMPT_RE = r'[>#]\s*$'   # device CLI prompt (flexible)

def run_command(child, cmd, timeout=25):
    """
    Run 'cmd' on the device and capture all output until the next prompt.
    Handles paging prompts like '--More--' by sending space.
    """
    child.sendline(cmd)
    output_chunks = []

    while True:
        i = child.expect(
            [r'--More--', r'-More-', r'More:.*', PROMPT_RE, pexpect.TIMEOUT],
            timeout=timeout
        )
        # Everything printed before the match
        output_chunks.append(child.before)

        if i in (0, 1, 2):          # pager variants
            child.send(" ")         # send SPACE to continue
            continue
        elif i == 3:                # saw device prompt again -> command finished
            break
        else:                       # TIMEOUT -> stop (best effort)
            break

    # Join, strip, and remove echoed command on first line if present
    raw = "".join(output_chunks)
    lines = raw.splitlines()
    if lines and lines[0].strip() == cmd:
        lines = lines[1:]
    return "\n".join(lines).rstrip()


def wait_until_in_device(child, dev_user, dev_pass, port, timeout=30):
    """
    After selecting a port in pmshell, wait until we are either:
      - at login/username/password (perform login); or
      - already at a device prompt.
    Returns True when inside device CLI, False if we should skip this port.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            i = child.expect(
                [r'[Ll]ogin:', r'[Uu]sername:', r'[Pp]assword:', PROMPT_RE,
                 r'Login incorrect', r'Permission denied', r'Port', pexpect.TIMEOUT],
                timeout=8
            )

            if i in (0, 1):  # login: or Username:
                child.sendline(dev_user)
                # Expect password next (or prompt if no password)
                j = child.expect([r'[Pp]assword:', PROMPT_RE], timeout=10)
                if j == 0:
                    child.sendline(dev_pass)
                    child.expect(PROMPT_RE, timeout=15)
                    return True
                else:
                    return True

            elif i == 2:     # Password: (password-only devices)
                child.sendline(dev_pass)
                child.expect(PROMPT_RE, timeout=15)
                return True

            elif i == 3:     # Already at device prompt
                return True

            elif i in (4, 5):  # Login incorrect / Permission denied
                print(f"?~]~L Authentication failed on port {port}. Skipping.")
                return False

            elif i == 6:  # Saw 'Port' again
    # If we're *immediately* back at Port menu, it's a failure
    # But sometimes device banners include 'Port' - check by re-expecting quickly
                try:
                    child.expect([r'[Ll]ogin:', r'[Uu]sername:', r'[Pp]assword:', PROMPT_RE], timeout=3)
        # If we got here, it's actually the device, not the menu
                    return True
                except pexpect.TIMEOUT:
                    print(f"?~Z| ?~O Port {port}: pmshell did not connect (back at Port menu). Skipping.")
                    return False
            else:            # TIMEOUT in this loop pass: just continue waiting
                continue

        except pexpect.TIMEOUT:
            # Keep looping until overall timeout
            continue

    print(f"?~Z| ?~O Port {port}: Timeout waiting for device login/prompt. Skipping.")
    return False


def ensure_in_pmshell(child):
    """
    Ensure we're at the Opengear pmshell 'Port>' menu.
    If at shell (#/$), enter pmshell.
    """
    try:
        idx = child.expect([r'Connect to port\s*>', r'Port\s*>', r'\$', r'#'], timeout=3)
        if idx in (0,1):
            return  # already in Port menu
        else:
            child.sendline("pmshell")
            child.expect([r'Connect to port\s*>',r'Port\s*>'], timeout=10)
    except pexpect.TIMEOUT:
        # best effort retry
        child.sendline("pmshell")
        child.expect([r'Connect to port\s*>',r'Port\s*>'], timeout=10)


def automate_opengear_multiple_ports():
    # -------- Login to Opengear --------
    host = input("Enter Opengear IP: ").strip()
    user = input("Enter Opengear username: ").strip()
    password = getpass.getpass("Enter Opengear password: ")

    ssh_cmd = f"ssh {user}@{host}"
    child = pexpect.spawn(ssh_cmd, encoding='utf-8')
    child.expect([r"[Pp]assword:"])
    child.sendline(password)
    child.expect(r'\$|#')   # Opengear shell prompt

    # -------- Ask for device creds once --------
    dev_user = input("Enter device username: ").strip()
    dev_pass = getpass.getpass("Enter device password: ")

    # -------- Ask for list of ports (comma-separated) --------
    ports_input = input("Enter port numbers (comma separated): ").strip()
    ports = [p.strip() for p in ports_input.split(",") if p.strip().isdigit()]

    # -------- Commands to run --------
    commands = [
        "show bgp summary",
        "show interface brief",
        "show lldp neighbor"
    ]

    for port in ports:
        print(f"\n========== Working on port {port} ==========")

        # Always start from pmshell Port menu
        ensure_in_pmshell(child)

        # Select port and confirm
        child.sendline(port)
        child.sendline("")   # confirm
        time.sleep(1.5)      # small settling delay

        # Ensure we're inside device (or skip)
        if not wait_until_in_device(child, dev_user, dev_pass, port, timeout=40):
            # Try to get back to pmshell cleanly
            child.send("%"); time.sleep(0.2); child.send("."); time.sleep(0.8)
            ensure_in_pmshell(child)
            continue

        # Run commands with paging handled
        for cmd in commands:
            print(f"\n--- Output of `{cmd}` on port {port} ---\n")
            output = run_command(child, cmd)
            print(output if output else "(no output)")

        # Exit device cleanly (per your sequence)
        child.sendline("exit")
        time.sleep(1)
        child.send("%"); time.sleep(0.2); child.send("."); time.sleep(0.8)
        # Land back in pmshell menu or bash, then normalize
        ensure_in_pmshell(child)

    print("\n?~\~E Automation complete for all ports.")

if __name__ == "__main__":
    automate_opengear_multiple_ports()

                                                  
