# writer Nurul Quamar

""" this script can login to Open-gear and initialise the host bootstrap on hosts connected to ports.
it need OG ip, user and password to login to OG and ports to work on."""

import pexpect 
import getpass 
import time 
def automate_opengear(): 
    host = input("Enter Opengear IP: ").strip() 
    user = input("Enter Opengear username: ").strip() 
    password = getpass.getpass("Enter Opengear password: ") 
    
    # Start SSH session 
    ssh_cmd = f"ssh {user}@{host}" 
    child = pexpect.spawn(ssh_cmd, encoding='utf-8') 
    child.logfile = None # set = sys.stdout if you want to debug 


    # Handle login
    i = child.expect([r"[Pp]assword:", r"yes/no", pexpect.EOF, pexpect.TIMEOUT])
    if i == 1:
        child.sendline("yes")
        child.expect([r"[Pp]assword:"])
    child.sendline(password)
    child.expect(r'\$|#')
    
    # Run pmshell 
    child.sendline("pmshell") 
    child.expect("Port") # waits for the pmshell menu 
    # Ask user for ports 
    ports_input = input("Enter port numbers (comma separated): ").strip() 
    ports = [int(p.strip()) 
            for p in ports_input.split(",") if p.strip().isdigit()] 
    for port in ports: 
        print(f"\n--- Working on port {port} ---")
    # Select port 
    child.sendline(str(port)) child.sendline("") # extra enter to confirm 
    time.sleep(2) # small delay to ensure connection opens 
    # Send keys one by one with slight delay 
    child.send("\x1b[D") # Left Arrow 
    time.sleep(0.2) 
    for _ in range(5): # 5 Down Arrows 
        child.send("\x1b[B") 
        time.sleep(0.3) #to hit enter 
        child.send("\r") 
        time.sleep(0.5) 
        #capture the screen after 5 sec 
        try: 
            child.expect(r">>Checking Media Presence......", timeout=3) 
            print(f"\n[Port {port}] Found: >>Checking Media Presence......") 
        except pexpect.TIMEOUT: 
            print(f"\n[Port {port}] Did NOT see expected message within 3s.") 
        # Exit back to pmshell 
        child.send("%") 
        time.sleep(0.2) 
        child.send(".") 
        time.sleep(1) 
        child.expect("Port") 
    # back at port selection menu 
    print("\n?~\~E Automation complete for ports") 
if __name__ == "__main__": 
    automate_opengear()
