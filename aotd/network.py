"""
@title

@description

"""
import subprocess


def check_ssid_visible(networks, ssid):
    visible = False
    for each_net in networks:
        ssid_keys = [
            each_key
            for each_key in each_net.keys()
            if each_key.lower().startswith('ssid')
        ]
        if len(ssid_keys) > 0:
            net_ssid = ssid_keys[0]
            ssid_name = each_net[net_ssid]
            if ssid_name == ssid:
                visible = True
    return visible


def connect_ssid(ssid):
    command = f'netsh wlan connect name={ssid}'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    success = 'Connection request was completed successfully' in stdout.decode('utf-8')
    return success


def parse_chunks(info_lines):
    interfaces_info = []
    boundaries = [i for i, x in enumerate(info_lines) if x == '\r']
    start = 0
    for each_boundary in boundaries:
        next_chunk = info_lines[start: each_boundary]
        next_chunk = {
            each_line.split(':')[0].strip(): each_line.split(':')[1].strip()
            for each_line in next_chunk
        }
        interfaces_info.append(next_chunk)
        start = each_boundary + 1
    return interfaces_info


def get_wlan_networks():
    command = ['netsh', 'wlan', 'show', 'network']
    proc_ret = subprocess.check_output(command)
    raw = proc_ret.decode('utf-8')
    raw = raw.split('\n')

    interfaces_parts = raw[2].split('interfaces')
    num_interfaces = interfaces_parts[0].strip().split(' ')
    num_interfaces = int(num_interfaces[2])

    info_lines = raw[4:-1]
    network_info = []
    if num_interfaces > 0:
        network_info = parse_chunks(info_lines)
    return network_info


def get_wlan_interfaces():
    wifi = subprocess.check_output(['netsh', 'WLAN', 'show', 'interfaces'])
    raw = wifi.decode('utf-8')
    raw = raw.split('\n')

    interfaces_parts = raw[1].split('interfaces')
    num_interfaces = interfaces_parts[0].strip().split(' ')
    num_interfaces = int(num_interfaces[-1])

    interfaces_info = []
    info_lines = raw[3:-3]
    if num_interfaces > 0:
        interfaces_info = parse_chunks(info_lines)
    return interfaces_info
