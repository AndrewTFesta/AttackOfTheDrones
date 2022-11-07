"""
@title

@description

"""
import argparse
import time

from aotd.network import get_wlan_interfaces, get_wlan_networks, connect_ssid, check_ssid_visible


def main(main_args):
    ssid = 'TELLO-5F487F'
    #################################
    interfaces = get_wlan_interfaces()
    networks = get_wlan_networks()

    active_interface = interfaces[0]
    active_ssid = active_interface['SSID'] if active_interface['State'].lower() == 'connected' else None

    if check_ssid_visible(networks, ssid):
        connected = connect_ssid(ssid)
        print(f'Connection to {ssid}: {connected}')

    time.sleep(5)
    active_interface = interfaces[0]
    new_ssid = active_interface['SSID'] if active_interface['State'].lower() == 'connected' else None
    if new_ssid == ssid:
        print(f'Verified connection to: {ssid}')

    if active_ssid:
        connected = connect_ssid(ssid)
        time.sleep(5)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
