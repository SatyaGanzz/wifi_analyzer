import os
import platform
import socket
import subprocess
import re
import requests
import psutil
import speedtest
import time
import sys
import threading
from datetime import datetime

# Mengimpor library untuk kustomisasi tampilan dan warna
from colorama import Fore, Style, init
try:
    from pyfiglet import figlet_format
except ImportError:
    figlet_format = None

# Inisialisasi colorama agar pewarnaan berfungsi di CMD/PowerShell Windows
init(autoreset=True)

def get_wifi_details_windows():
    """Extracts deep Wi-Fi details including signal strength and encryption on Windows"""
    wifi_info = {"signal": "Not detected", "dbm": "N/A", "auth": "Not detected", "ssid": "Not detected", "password": "N/A"}
    try:
        meta_data = subprocess.check_output(["netsh", "wlan", "show", "interfaces"]).decode('utf-8', errors='ignore')
        
        ssid_match = re.search(r"SSID\s*:\s*(.*)", meta_data)
        if ssid_match:
            wifi_info["ssid"] = ssid_match.group(1).strip()
            
        auth_match = re.search(r"Authentication\s*:\s*(.*)", meta_data)
        if auth_match:
            wifi_info["auth"] = auth_match.group(1).strip()
            
        signal_match = re.search(r"Signal\s*:\s*(\d+)%", meta_data)
        if signal_match:
            percentage = int(signal_match.group(1).strip())
            wifi_info["signal"] = f"{percentage}%"
            dbm = int((percentage / 2) - 100)
            wifi_info["dbm"] = f"{dbm} dBm"
            
        if wifi_info["ssid"] != "Not detected":
            try:
                profile_data = subprocess.check_output(
                    ['netsh', 'wlan', 'show', 'profile', wifi_info["ssid"], 'key=clear']
                ).decode('utf-8', errors='ignore')
                password_match = re.search(r"Key Content\s*:\s*(.*)", profile_data)
                if password_match:
                    wifi_info["password"] = password_match.group(1).strip()
                else:
                    wifi_info["password"] = "(Open Network / No Password)"
            except Exception:
                wifi_info["password"] = "(Could not extract)"
                
    except Exception:
        pass
    return wifi_info

def get_wifi_ssid():
    """Retrieves the SSID based on OS"""
    os_name = platform.system()
    if os_name == "Windows":
        return get_wifi_details_windows()["ssid"]
    elif os_name == "Linux":
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"]).decode('utf-8').strip()
            return ssid if ssid else "Connected (Ethernet/Unknown)"
        except Exception:
            pass
    return "Not detected (Wi-Fi off / Limited permissions)"

def get_network_details():
    """Retrieves local IP, MAC Address, Subnet Mask, and Gateway"""
    details = {}
    interfaces = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    
    for intf, addrs in interfaces.items():
        if intf in stats and stats[intf].isup and "loopback" not in intf.lower():
            for addr in addrs:
                if addr.family == socket.AF_INET: # IPv4
                    details['ip'] = addr.address
                    details['subnet'] = addr.netmask
                    
    for intf, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK: # MAC Address
                if details.get('ip') and addr.address: 
                    details['mac'] = addr.address
                    break

    gateway = "Not found"
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output("route print 0.0.0.0", shell=True).decode('utf-8', errors='ignore')
            match = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+(\S+)", out)
            if match: gateway = match.group(1)
        elif platform.system() == "Linux":
            out = subprocess.check_output("ip route show | grep default", shell=True).decode('utf-8')
            gateway = out.split()[2]
    except Exception:
        pass
    details['gateway'] = gateway
    return details

def get_geo_location():
    """Fetches Public IP and Region/Location details using a free API"""
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5).json()
        return {
            "public_ip": response.get("ip"),
            "city": response.get("city"),
            "region": response.get("region"),
            "country": response.get("country"),
            "isp": response.get("org")
        }
    except Exception:
        return {"error": "Failed to fetch region data (Check your internet connection)"}

def clear_lines(count):
    """Clears a specific number of lines above the cursor in the terminal"""
    for _ in range(count):
        sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()

def text_spinner(stop_event, message):
    """Displays a running text animation with changing dots"""
    spinners = [".  ", ".. ", "...", ".. "]
    idx = 0
    while not stop_event.is_set():
        timestamp = datetime.now().strftime('%H:%M:%S')
        sys.stdout.write(Fore.WHITE + Style.BRIGHT + f"\r[{timestamp}] {message}{spinners[idx % 4]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.4)

def scan_single_port(target_ip, port, service, open_ports_list):
    """Worker function to scan a single port"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    result = s.connect_ex((target_ip, port))
    if result == 0:
        open_ports_list.append((port, service))
    s.close()

def run_port_scanner(target_ip):
    """Scans popular ports using multithreading for maximum speed"""
    popular_ports = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 139: "NetBIOS", 443: "HTTPS", 
        445: "SMB", 3306: "MySQL", 8080: "HTTP-Alt"
    }
    
    print(Fore.YELLOW + f"\n[+] Scanning popular ports on Gateway ({target_ip})...")
    
    threads = []
    open_ports = []
    
    for port, service in popular_ports.items():
        t = threading.Thread(target=scan_single_port, args=(target_ip, port, service, open_ports))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    if open_ports:
        open_ports.sort(key=lambda x: x[0])
        for port, service in open_ports:
            print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" Port {port:<5} [{service:<8}] : " + Fore.LIGHTGREEN_EX + "OPEN (Exposed)")
    else:
        print(Fore.WHITE + Style.BRIGHT + " [*] No popular ports are openly exposed on this gateway.")

def run_speedtest():
    """Runs an automatic speed test with smooth terminal updates and animations"""
    print(Fore.YELLOW + "\n[+] Initializing Speedtest...")
    stop_anim = threading.Event()
    
    try:
        t = threading.Thread(target=text_spinner, args=(stop_anim, "Finding the best server"))
        t.start()
        st = speedtest.Speedtest()
        st.get_best_server()
        stop_anim.set()
        t.join()
        
        stop_anim.clear()
        t = threading.Thread(target=text_spinner, args=(stop_anim, "Testing Download Speed (Please wait)"))
        t.start()
        download_speed = st.download() / 1_000_000
        stop_anim.set()
        t.join()
        
        stop_anim.clear()
        t = threading.Thread(target=text_spinner, args=(stop_anim, "Testing Upload Speed (Please wait)"))
        t.start()
        upload_speed = st.upload() / 1_000_000
        stop_anim.set()
        t.join()
        
        ping = st.results.ping
        clear_lines(4)
        
        return {
            "download": f"{download_speed:.2f} Mbps",
            "upload": f"{upload_speed:.2f} Mbps",
            "ping": f"{ping:.3f} ms"
        }
    except Exception as e:
        if 't' in locals() and t.is_alive():
            stop_anim.set()
            t.join()
        return {"error": f"Speedtest failed to execute: {e}"}

# --- FITUR UTILITY JARINGAN ---

def run_wifi_analysis():
    """Runs the core network analysis, geolocation check, port scan, speedtest, and extracts password"""
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + Fore.WHITE + "=" * 50)
    print(Fore.MAGENTA + Style.BRIGHT + "         WIFI & NETWORK ANALYSIS TOOL          ")
    print(Fore.CYAN + Style.BRIGHT + f"         Started at: {start_time}")
    print(Fore.WHITE + "=" * 50)
    
    w = 17
    wifi_details = {"ssid": "Not detected", "auth": "N/A", "signal": "N/A", "dbm": "N/A", "password": "N/A"}
    
    # 1. Wi-Fi SSID, Signal Strength & PASSWORD Extractor Analysis
    print(Fore.YELLOW + "[+] Analyzing Wi-Fi Connection Details...")
    if platform.system() == "Windows":
        wifi_details = get_wifi_details_windows()
        sig_num = int(wifi_details["signal"].replace("%","")) if wifi_details["signal"] != "Not detected" else 0
        sig_color = Fore.GREEN if sig_num >= 75 else (Fore.YELLOW if sig_num >= 50 else Fore.RED)
        
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Wi-Fi SSID':<{w}}: {wifi_details['ssid']}")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Security Type':<{w}}: {wifi_details['auth']}")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Signal Quality':<{w}}: " + sig_color + f"{wifi_details['signal']} ({wifi_details['dbm']})")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Wi-Fi Password':<{w}}: " + Fore.LIGHTCYAN_EX + Style.BRIGHT + f"{wifi_details['password']}")
    else:
        wifi_details["ssid"] = get_wifi_ssid()
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Wi-Fi SSID':<{w}}: {wifi_details['ssid']}")
    
    # 2. Local IP Details Check
    net_info = get_network_details()
    local_ip = net_info.get('ip', 'Not detected')
    gateway_ip = net_info.get('gateway', 'Not detected')
    
    print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Local IP Addr':<{w}}: " + Fore.CYAN + Style.BRIGHT + f"{local_ip}")
    print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Subnet Mask':<{w}}: {net_info.get('subnet', 'Not detected')}")
    
    if gateway_ip != "Not found" and gateway_ip != "Not detected":
        ip_part = Fore.CYAN + Style.BRIGHT + f"{gateway_ip}"
        link_part = Fore.LIGHTBLUE_EX + "\033[4m" + f"http://{gateway_ip}" + "\033[24m"
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Default Gateway':<{w}}: {ip_part} " + Fore.WHITE + "/" + f" {link_part}")
    else:
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Default Gateway':<{w}}: " + Fore.RED + f"{gateway_ip}")
        
    print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'MAC Address':<{w}}: {net_info.get('mac', 'Not detected')}")
    
    # 3. IP Geo-location Check
    print(Fore.YELLOW + "\n[+] Fetching IP Geolocation Details...")
    geo_info = get_geo_location()
    if "error" not in geo_info:
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Public IP':<{w}}: " + Fore.CYAN + Style.BRIGHT + f"{geo_info['public_ip']}")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'ISP Provider':<{w}}: {geo_info['isp']}")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Region Location':<{w}}: {geo_info['city']}, {geo_info['region']}, {geo_info['country']}")
    else:
        print(Fore.RED + f"[-] {geo_info['error']}")
        geo_info = {"public_ip": "N/A", "isp": "N/A", "city": "N/A", "region": "N/A", "country": "N/A"}
        
    # 4. Port Scanning Feature
    if gateway_ip and gateway_ip != "Not found" and gateway_ip != "Not detected":
        run_port_scanner(gateway_ip)
    else:
        print(Fore.RED + "\n[-] Gateway not found. Skipping Port Scan.")
        
    # 5. Speedtest
    speed_info = run_speedtest()
    print(Fore.YELLOW + "\n[=] SPEEDTEST RESULTS [=]")
    if "error" not in speed_info:
        print(Fore.GREEN + "[*]" + Fore.BLUE + Style.BRIGHT + f" {'Download':<{w}}: {speed_info['download']}")
        print(Fore.GREEN + "[*]" + Fore.MAGENTA + Style.BRIGHT + f" {'Upload':<{w}}: {speed_info['upload']}")
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" {'Ping Latency':<{w}}: {speed_info['ping']}")
    else:
        print(Fore.RED + f"[-] {speed_info['error']}")
        speed_info = {"download": "N/A", "upload": "N/A", "ping": "N/A"}

    print(Fore.WHITE + "=" * 50)
    print(Fore.CYAN + Style.BRIGHT + f"       Main Analysis Finished at: {datetime.now().strftime('%H:%M:%S')}       ")
    print(Fore.WHITE + "=" * 50)
    
    # SYSTEM LOG REPORT GENERATOR (TERSTRUKTUR RAPI KE BAWAH)
    try:
        with open("network_report.txt", "a") as f:
            f.write(f"==================================================\n")
            f.write(f" NETWORK ANALYSIS REPORT | {start_time}\n")
            f.write(f"==================================================\n")
            f.write(f" [WI-FI DETAILS]\n")
            f.write(f"  SSID             : {wifi_details.get('ssid', 'N/A')}\n")
            f.write(f"  Security         : {wifi_details.get('auth', 'N/A')}\n")
            f.write(f"  Signal Strength  : {wifi_details.get('signal', 'N/A')} ({wifi_details.get('dbm', 'N/A')})\n")
            f.write(f"  Password         : {wifi_details.get('password', 'N/A')}\n\n")
            f.write(f" [LOCAL NETWORK]\n")
            f.write(f"  Local IP Address : {local_ip}\n")
            f.write(f"  Subnet Mask      : {net_info.get('subnet', 'N/A')}\n")
            f.write(f"  Default Gateway  : {gateway_ip}\n")
            f.write(f"  MAC Address      : {net_info.get('mac', 'N/A')}\n\n")
            f.write(f" [PUBLIC INTEL]\n")
            f.write(f"  Public IP        : {geo_info.get('public_ip', 'N/A')}\n")
            f.write(f"  ISP Provider     : {geo_info.get('isp', 'N/A')}\n")
            f.write(f"  Location         : {geo_info.get('city', 'N/A')}, {geo_info.get('region', 'N/A')}, {geo_info.get('country', 'N/A')}\n\n")
            f.write(f" [SPEEDTEST RESULTS]\n")
            f.write(f"  Download Speed   : {speed_info.get('download', 'N/A')}\n")
            f.write(f"  Upload Speed     : {speed_info.get('upload', 'N/A')}\n")
            f.write(f"  Ping Latency     : {speed_info.get('ping', 'N/A')}\n")
            f.write(f"==================================================\n\n\n")
        print(Fore.GREEN + " [Report] Results successfully structured inside 'network_report.txt'")
    except Exception as e:
        print(Fore.RED + f" [Report] Error writing to log file: {e}")

def run_whois_lookup():
    """Performs an advanced WHOIS intelligence lookup via free JSON API"""
    print(Fore.YELLOW + "\n[+=] IP/DOMAIN INTEL WHOIS LOOKUP [+=]")
    target = input(Fore.WHITE + Style.BRIGHT + " [?] Enter Target IP or Domain Name (e.g., 8.8.8.8): ").strip()
    if not target:
        print(Fore.RED + " [-] Target cannot be empty.")
        return
    try:
        print(Fore.WHITE + f" [*] Querying WHOIS Database for {target}...")
        response = requests.get(f"https://ipapi.co/{target}/json/", timeout=5).json()
        
        if "error" not in response:
            print(Fore.GREEN + " [+] IP Target    : " + Fore.CYAN + Style.BRIGHT + response.get("ip", target))
            print(Fore.GREEN + " [+] Organization : " + Fore.CYAN + Style.BRIGHT + response.get("org", "N/A"))
            print(Fore.GREEN + " [+] ASN Code     : " + Fore.WHITE + Style.BRIGHT + response.get("asn", "N/A"))
            print(Fore.GREEN + " [+] Country/City : " + Fore.WHITE + Style.BRIGHT + f"{response.get('city')}, {response.get('country_name')}")
            print(Fore.GREEN + " [+] Latitude/Long: " + Fore.LIGHTBLACK_EX + f"{response.get('latitude')}, {response.get('longitude')}")
        else:
            print(Fore.RED + f" [-] API Error: {response.get('reason', 'Invalid input structure')}")
    except Exception as e:
        print(Fore.RED + f" [-] Network Error: Fails to fetch target analytics ({e})")

def run_dns_resolver():
    """Resolves a domain name to its corresponding IP address"""
    print(Fore.YELLOW + "\n[+=] DNS DOMAIN IP RESOLVER [+=]")
    domain = input(Fore.WHITE + Style.BRIGHT + " [?] Enter Target Domain (e.g., google.com): ").strip()
    if not domain:
        print(Fore.RED + " [-] Target domain cannot be empty.")
        return
    try:
        print(Fore.WHITE + f" [*] Resolving {domain}...")
        resolved_ip = socket.gethostbyname(domain)
        print(Fore.GREEN + " [+] Target Domain : " + Fore.WHITE + Style.BRIGHT + domain)
        print(Fore.GREEN + " [+] Resolved IP   : " + Fore.CYAN + Style.BRIGHT + resolved_ip)
    except Exception:
        print(Fore.RED + " [-] Failed to resolve domain. Check connection or spelling.")

def ping_worker(ip_prefix, host_num, active_hosts):
    """Helper worker to ping a single host address"""
    target_ip = f"{ip_prefix}.{host_num}"
    param = "-n" if platform.system() == "Windows" else "-c"
    timeout_param = "-w" if platform.system() == "Windows" else "-W"
    timeout_val = "200" if platform.system() == "Windows" else "1"
    try:
        with open(os.devnull, 'wb') as devnull:
            output = subprocess.call(["ping", param, "1", timeout_param, timeout_val, target_ip], stdout=devnull, stderr=devnull)
        if output == 0:
            active_hosts.append(target_ip)
    except Exception:
        pass

def run_host_discovery():
    """Scans the local subnet for active devices using multithreading"""
    print(Fore.YELLOW + "\n[+=] LOCAL NETWORK DEVICE SCANNER [+=]")
    net_info = get_network_details()
    local_ip = net_info.get('ip', 'Not detected')
    
    if not local_ip or local_ip == "Not detected":
        print(Fore.RED + " [-] Active local IP not found. Cannot determine subnet prefix.")
        return
    
    ip_parts = local_ip.split('.')
    if len(ip_parts) != 4:
        print(Fore.RED + " [-] Error parsing local IP structure.")
        return
    
    ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
    active_hosts = []
    threads = []
    
    print(Fore.WHITE + f" [*] Scanning subnet range {ip_prefix}.1 to {ip_prefix}.255...")
    
    for i in range(1, 255):
        t = threading.Thread(target=ping_worker, args=(ip_prefix, i, active_hosts))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print(Fore.GREEN + f" [*] Scan finished! Found {len(active_hosts)} active device(s) on Wi-Fi:\n" + Fore.WHITE + "="*50)
    active_hosts.sort(key=lambda x: int(x.split('.')[-1]))
    for host in active_hosts:
        marker = " (Your Device)" if host == local_ip else ""
        print(Fore.GREEN + "  [+]" + Fore.WHITE + Style.BRIGHT + f" Active Host : {host:<15}" + Fore.CYAN + Style.BRIGHT + marker)

def run_jitter_test():
    """Tests connection stability and calculates ping jitter"""
    print(Fore.YELLOW + "\n[+=] CONNECTION STABILITY & JITTER TEST [+=]")
    target = "8.8.8.8"
    print(Fore.WHITE + f" [*] Sending 10 sequential packets to {target} to calculate stability...")
    
    param = "-n" if platform.system() == "Windows" else "-c"
    pings = []
    
    for i in range(1, 11):
        try:
            start_t = time.time()
            with open(os.devnull, 'wb') as devnull:
                res = subprocess.call(["ping", param, "1", target], stdout=devnull, stderr=devnull)
            end_t = (time.time() - start_t) * 1000
            
            if res == 0:
                pings.append(end_t)
                print(Fore.GREEN + f"  [+] Packet {i:<2}: SUCCESS | Time = {end_t:.2f} ms")
            else:
                print(Fore.RED + f"  [-] Packet {i:<2}: PACKET LOSS / TIMEOUT")
        except Exception:
            pass
        time.sleep(0.2)
        
    if len(pings) > 1:
        avg_ping = sum(pings) / len(pings)
        jitters = [abs(pings[j] - pings[j-1]) for j in range(1, len(pings))]
        avg_jitter = sum(jitters) / len(jitters)
        loss = ((10 - len(pings)) / 10) * 100
        
        print(Fore.WHITE + "="*50)
        print(Fore.GREEN + "[*]" + Fore.WHITE + Style.BRIGHT + f" Average Latency : {avg_ping:.2f} ms")
        print(Fore.GREEN + "[*]" + Fore.MAGENTA + Style.BRIGHT + f" Network Jitter  : {avg_jitter:.2f} ms")
        print(Fore.GREEN + "[*]" + (Fore.GREEN if loss == 0 else Fore.RED) + Style.BRIGHT + f" Packet Loss     : {loss:.1f}%")
    else:
        print(Fore.RED + " [-] Stablity test failed due to complete packet loss.")

def check_bottom_navigation():
    """Handles prompt navigation after a utility function finishes execution"""
    print(Fore.WHITE + Style.BRIGHT + "\n    Press Enter to return to the menu or type 'e' to exit... ", end="")
    user_input = input().strip().lower()
    if user_input == 'e':
        print(Fore.GREEN + "\n    [+] Thank you for using Satyaghani tools. Goodbye!")
        sys.exit()

def start_boot_loading():
    """Simulates a cyberpunk loading sequence with exact 3.5s duration and colored bars"""
    print(Fore.GREEN + Style.BRIGHT + " LOADING TOOLS.....")
    print(Fore.CYAN + Style.BRIGHT + "tools by satyaghani".center(65, " "))
    print()
    time.sleep(0.3)
    
    components = [
        "Network Interfaces", 
        "Socket Modules", 
        "Speedtest Engine", 
        "Colorama Graphics", 
        "WHOIS Analytics Engine"
    ]
    
    for comp in components:
        sys.stdout.write(Fore.GREEN + "  [*] " + Fore.WHITE + Style.BRIGHT + f"Loading {comp:<24} ")
        sys.stdout.flush()
        
        slots = 10
        for i in range(slots + 1):
            bar = Fore.CYAN + '■' * i + Fore.LIGHTBLACK_EX + ' ' * (slots - i)
            percent = Fore.YELLOW + f"{int((i / slots) * 100)}%"
            
            sys.stdout.write(f"\r  [*] Loading {comp:<24} [{bar}] {percent}")
            sys.stdout.flush()
            time.sleep(0.052) # Tepat 52 ms per slot biar total durasi sinkron 3.5 detik
            
        print(Fore.WHITE + " ... " + Fore.GREEN + Style.BRIGHT + "OK")
        time.sleep(0.05)
        
    print(Fore.GREEN + Style.BRIGHT + "\n " + "■"*17 + " ALL TOOLS LOADED SUCCESSFULLY! " + "■"*17)
    print(Fore.CYAN + Style.BRIGHT + " READY TO RUN ".center(65, " "))
    time.sleep(0.6)

# --- MAIN PROGRAM ---
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    start_boot_loading()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        text_to_render = "Wifi Analysis"
        if figlet_format:
            try:
                art = figlet_format(text_to_render, font="slant")
            except Exception:
                art = figlet_format(text_to_render)
        else:
            art = f"=== {text_to_render} ==="

        # Banner Utama
        print(Fore.RED + Style.BRIGHT + art)
        print(Fore.CYAN + Style.BRIGHT + "tools by satyaghani".center(65, " "))
        
        # Tampilan Menu Berjumlah 6 Opsi
        padding = "    "
        print(Fore.YELLOW + Style.BRIGHT + "========================== TOOLS MENU ==========================")
        print(padding + Fore.WHITE + Style.BRIGHT + "[1] Wifi Analysis (SSID, IP, Geo, Ports, Speedtest, Pass)")
        print(padding + Fore.WHITE + Style.BRIGHT + "[2] Advanced IP/Domain Intel WHOIS Lookup")
        print(padding + Fore.WHITE + Style.BRIGHT + "[3] DNS Domain Resolver (Domain -> IP)")
        print(padding + Fore.WHITE + Style.BRIGHT + "[4] Discover Active Devices on Wi-Fi (Subnet Scanner)")
        print(padding + Fore.WHITE + Style.BRIGHT + "[5] Connection Stability & Jitter Test (10x Packets)")
        print(padding + Fore.RED + Style.BRIGHT + "[6] Exit Tools")
        print(Fore.YELLOW + Style.BRIGHT + "================================================================")
        
        print(Fore.WHITE + Style.BRIGHT + "\n    Choose an option (1-6): ", end="")
        menu_choice = input().strip()
        
        if menu_choice == '1':
            run_wifi_analysis()
            check_bottom_navigation()
        elif menu_choice == '2':
            run_whois_lookup()
            check_bottom_navigation()
        elif menu_choice == '3':
            run_dns_resolver()
            check_bottom_navigation()
        elif menu_choice == '4':
            run_host_discovery()
            check_bottom_navigation()
        elif menu_choice == '5':
            run_jitter_test()
            check_bottom_navigation()
        elif menu_choice == '6':
            print(Fore.GREEN + "\n    [+] Thank you for using Satyaghani tools. Goodbye!")
            break
        else:
            print(Fore.RED + "    [-] Invalid choice, please enter 1, 2, 3, 4, 5, or 6.")
            time.sleep(1.5)