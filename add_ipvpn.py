#!/usr/bin/env python3
# encoding: utf-8

import yaml
import argparse
from ipcalc import Network
from glob import glob
from jinja2 import Template, Environment, FileSystemLoader
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from pprint import pprint as pp

from define import BASEFOLDER, TEMPLATES


def parse_args(args=None):
    """
    Parse the arguments/options passed to the program on the command line.
    """

    parser = argparse.ArgumentParser(description=__doc__,
                        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('devices', type=str, metavar='devices')
    parser.add_argument('-pp', '--pprint-only', dest='pp', action='store_true')

    subparsers = parser.add_subparsers(help='sub-command help')

    ipvpn = subparsers.add_parser('ipvpn', help='ipvpn only')
    ipvpn.set_defaults(which='ipvpn')
    ipvpn.add_argument('-n', '--number-of-vpns', type=int, dest='nvpns')
    ipvpn.add_argument('-vid', '--first-vpn-id', type=int, dest='vid')
    ipvpn.add_argument('-nu', '--number-of-units', type=int, dest='nu')
    ipvpn.add_argument('-nid', '--first-unit-id', type=int, dest='nid')

    vpws = subparsers.add_parser('vpws', help='vpws only')
    vpws.set_defaults(which='vpws')
    vpws.add_argument('-n', '--number-of-vpns', type=int, dest='nvpns')
    vpws.add_argument('-vid', '--first-vpn-id', type=int, dest='vid')

    vpls = subparsers.add_parser('vpls', help='vpls only')
    vpls.set_defaults(which='vpls')
    vpls.add_argument('-n', '--number-of-vpns', type=int, dest='nvpns')
    vpls.add_argument('-vid', '--first-vpn-id', type=int, dest='vid')
    vpls.add_argument('-nid', '--first-unit-id', type=int, dest='nid')
    vpls.add_argument('-oid', '--first-outer-vlan-id', type=int, dest='oid')

    (args, rest_args) = parser.parse_known_args()

    return args

def show_diff(cu):
    """
    show configuration | compare
    """
    return cu.diff()

def commit(cu):
    """
    issues commit check follofs commit if everything is fine,
    prints error otherwise
    """
    if cu.commit_check():
        if cu.commit():
            print("Done")
    else:
        print("Something is wrong with commit")
        return

def push(hostname, config):
    if args.pp:
        print(config)
    else:
        dev = Device(hostname, user='admin', password='admin')
        dev.open(gather_facts=False)
        dev.timeout = 60
        dev.bind(cu=Config)
        with Config(dev, mode='private') as cu:
            rsp = cu.load(config, format='text', merge=True)
            diff = show_diff(cu)
            if diff:
                print(diff)
            #    commit(cu)
            cu.rollback()

def do_ipvpn(device, **kwargs):
    def _do_routing_insatnce():
        template = env.get_template('ipvpn/routing-instances.j2')
        print(kwargs['name'])
        vpns = range(args.vid, args.vid+args.nvpns)
        units = range(args.nid, args.nid+args.nu)
        return template.render({'vpns': vpns, 
                                'units': units,
                                'base_interface': kwargs['base_interface'],
                                'rd': kwargs['rd'],
                                'number_of_units': args.nu
                                })

    def _do_interfaces():
        net = Network('{}'.format(kwargs['ipvpn_ipnet']))
        ipv6net = Network(u'{}'.format(kwargs['ipvpn_ipv6net']))
        template = env.get_template('ipvpn/interfaces.j2')
        vpns = [ str(vpn) for vpn in range(args.vid, args.vid+args.nvpns)]
        outer_offest, inner_offset = kwargs['vlan_offsets'].split(' ')
        return template.render({'vpns':vpns,
                                'units': range(args.nid, args.nid+args.nu),
                                'base_interface': kwargs['base_interface'],
                                'subnets': [ net+i*256 for i in range(1, args.nu+1)], 
                                'v6subnets': [ ipv6net+i*65536 for i in range(1, args.nu+1)], 
                                'gw': 1,
                                'inner_vlans': list(range(1, args.nu+1)),
                                'nu': args.nu,
                                'inner_offset': int(inner_offset),
                                'outer_offset': int(outer_offest)
                                })

    device_config = ''
    device_config += _do_routing_insatnce() + '\n'
    device_config += _do_interfaces() + '\n'
    push(device, device_config)

def do_vpws(device, **kwargs):
    def _do_routing_insatnce():
        template = env.get_template('vpws/routing-instances.j2')
        print(kwargs['name'])
        vpns = range(args.vid, args.vid+args.nvpns)
        return template.render({'vpns': vpns, 
                                'base_interface': kwargs['base_interface'],
                                'rd': kwargs['rd'],
                                'side': kwargs['side']
                                })

    def _do_interfaces():
        template = env.get_template('vpws/interfaces.j2')
        vpns = [ str(vpn) for vpn in range(args.vid, args.vid+args.nvpns)]
        outer_offest, inner_offset = kwargs['vlan_offsets'].split(' ')
        inner_vlans = list(range(1, 11))
        esis = []
        esi = True if kwargs['side'] == 'right' else None
        for i in range(args.vid, args.vid+len(vpns)+1):
            s = "{0:020d}".format(i)
            esis.append(":".join(a+b for a,b in zip(s[::2], s[1::2])))

        return template.render({'vpns':vpns,
								'esi_exists': esi,
								'esis': esis,
                                'inner_vlans': len(vpns)*inner_vlans,
                                'base_interface': kwargs['base_interface'],
                                'inner_offset': int(inner_offset),
                                'outer_offset': int(outer_offest)
                                })

    device_config = ''
    device_config += _do_routing_insatnce() + '\n'
    device_config += _do_interfaces() + '\n'
    push(device, device_config)

def do_vpls(device, **kwargs):
    def _do_routing_insatnce():
        template = env.get_template('vpls/routing-instances.j2')
        print(kwargs['name'])
        vpns = range(args.vid, args.vid+args.nvpns)
        units = list(range(30))
        return template.render({'vpns': vpns, 
                                'base_interface': kwargs['base_interface'],
                                'rd': kwargs['rd'],
                                'side': kwargs['side'],
                                'units': units,
                                'base_unit': args.nid
                                })

    def _do_interfaces():
        template = env.get_template('vpls/interfaces.j2')
        vpns = [ str(vpn) for vpn in range(args.vid, args.vid+args.nvpns)]
        outer_offest, inner_offset = kwargs['vlan_offsets'].split(' ')
        inner_vlans = list(range(1, 31))
        outer_vlans = [ i for i in list(range(args.oid, args.oid+args.nvpns+1)) for y in inner_vlans ]
        left_vpns = [ i for i in vpns for y in inner_vlans ]
        esis = []
        esi = True if kwargs['side'] == 'right' else None
        left_units = list(range(args.nid, args.nid+args.nvpns*30))
        right_units = list(range(args.nid, args.nid+args.nvpns*30, 30))
        for i in right_units:
            s = "{0:020d}".format(i)
            esis.append(":".join(a+b for a,b in zip(s[::2], s[1::2])))

        return template.render({'vpns': vpns,
                                'left_vpns': left_vpns,
                                'left_units': left_units,
                                'right_units': right_units,
								'esi_exists': esi,
								'esis': esis,
                                'inner_vlans': len(vpns)*inner_vlans,
                                'outer_vlans': outer_vlans,
                                'base_interface': kwargs['base_interface'],
                                'inner_offset': int(inner_offset),
                                'outer_offset': int(outer_offest),
                                'side': kwargs['side']
                                })

    device_config = ''
    device_config += _do_routing_insatnce() + '\n'
    device_config += _do_interfaces() + '\n'
    push(device, device_config)

if __name__ == '__main__':
    args = parse_args()
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    env.globals.update(zip=zip)
    env.globals.update(enum=enumerate)

    with open(args.devices, 'r') as f:
        device_dict = yaml.safe_load(f)
    devices = device_dict['PEs']
    if args.which == 'ipvpn':
        for device in devices.items():
            if 'ipvpn' in device[1]['vpn_types']:
                do_ipvpn(device[0], **device[1])
    elif args.which == 'vpws':
        for device in devices.items():
            if 'vpws' in device[1]['vpn_types']:
                do_vpws(device[0], **device[1])
    elif args.which == 'vpls':
        for device in devices.items():
            if 'vpls' in device[1]['vpn_types']:
                do_vpls(device[0], **device[1])

