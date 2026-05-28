<div align="center">

# 📶 Wifi Analyzer

### A program using Python to analyze Wi-Fi connections.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

<align="center" img src="/img/banner.png">

---
## 📖 Description
**Wifi Analyzer** is a Python-based tool designed to analyze the quality, signal strength, and details of surrounding Wi-Fi connections. This program simplifies network monitoring and helps diagnose connectivity issues directly through the terminal or the provided interface.

> ⚠️ **Note:** Don't forget to configure your `.env` file before running the server.

---

## 🌠 Feature
* **Complete Wifi Analysis:** Instantly extracts active SSID data, authentication standards, current signal metrics (percentage and noise floor in dBm), and retrieves your saved Wi-Fi profile encryption key natively.
* **Local Subnet Asset Scanner:** Utilizes dynamic multithreading logic to map live nodes on your private IP segment (`/24` ranges) to run host discovery smoothly.
* **Interactive Admin Gateway Access:** Automatically parses your upstream default gateway routing table and prints out a dual clickable hyperlink standard (`http://gateway_ip`) directly inside modern terminal subshells for rapid access to router management panels.
* **Geographic Threat Intelligence & WHOIS:** Queries free remote REST APIs to pull your public-facing IPv4 lease information, ASN blocks, registered Internet Service Provider (ISP), and current municipal/regional map telemetry.
* **Asynchronous Network Diagnostics:** Runs multi-threaded socket probes across default administrative ports and handles multi-packet structural latency analyses to calculate jitter deviations and transmission packet loss.
* **Live Bandwidth Telemetry:** Features a sub-second network interface I/O listener tracking data throughput to log raw metrics, calculating current download/upload bitrates alongside aggregate bandwidth data consumption.
* **Cyberpunk Command Interface:** Packaged with a beautifully styled boot sequence executing a mathematically precision-timed 3.5-second runtime load bar using raw ANSI color mappings.

---

## 🛠️ Prerequisites
Before running this project, ensure your system has:
- Python 3.8 or higher
- `sudo` privileges (required for certain network scanning commands on Linux)

---

## 🚀 Getting Started

### 1. Clone the Repository
First, clone this repository to your local machine and navigate into the project directory:
```bash
git clone https://github.com/SatyaGanzz/wifi_analyzer
cd wifi_analyzer
```

### 2. Installation
Second, install requirement:
``` bash
sudo apt update && apt upgrade -y
sudo apt install python3-pip -y
pip3 install -r requirements.txt
```
### 3. Run
Last, run the project:
``` bash
sudo python3 wifi_analyzer.py
```
---

<h1 align="center"> <b>  🖼️Preview Output </h1>

<p align="center">
  <img src="/img/demo1.png" alt="Example output" width="800"/><br>
  <code><br>Loading<pentest_output></code>
</p>

<p align="center">
  <img src="/img/demo2.png" alt="Example output" width="800"/><br>
  <code><br>Menu<pentest_output></code>
</p>

<p align="center">
  <img src="/img/demo3.png" alt="Example output" width="800"/><br>
  <code><br>Choose 1<pentest_output></code>
</p>

---
&copy; SatyaGanzz