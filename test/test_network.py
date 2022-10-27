"""
@title

@description

"""
import argparse
import socket

import netifaces


def main(main_args):
    # Showing gateway list
    netifaces.gateways()

    # Getting interfaces
    interfaces = netifaces.interfaces()

    # Showing interfaces
    print('\n'.join(interfaces))

    # Getting interface info
    print(netifaces.ifaddresses(str(interfaces[0])))

    # Getting interface status
    addrs = netifaces.ifaddresses(str(interfaces[0]))
    print(addrs[netifaces.AF_INET])
    print(addrs[netifaces.AF_LINK])

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
