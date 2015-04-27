#!/usr/bin/python

import configargparse
import boto
import boto.ec2
import boto.exception
import collections
import os
import sys
import tabulate

aws_regions = boto.ec2.regions() 

discovered_instances = collections.OrderedDict((('#', []), ('IP Address', []), ('Name', [])))

parser = configargparse.ArgParser(default_config_files=['~/.aws_ssh'])
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('search', nargs='?', help='Search for an instance with any tag value <search>')
group.add_argument('-a', '--advanced', dest='filters', action='append', help='Advanced filtering, separate keys from values using = sign, like tag:environmentName=production. For more filters see http://docs.aws.amazon.com/AWSEC2/latest/CommandLineReference/ApiReference-cmd-DescribeInstances.html')
parser.add_argument('-u', '--user', dest='ssh_user', action='store', env_var='AWS_SSH_USER', required=True, help='User to SSH as')
args = parser.parse_args()

def perform_ssh(ip_address):
    if args.ssh_user:
        ip_address = args.ssh_user + '@' + ip_address 

    print("Connecting to %s" % ip_address)

    os.system('ssh ' + ip_address) 

def getReservationsFromFilter(blewp):
    # -a wasn't passed in, search all tags
    if args.search:
        return connection.get_all_reservations(None, {"tag-value": args.search})
    else:
        # -a was passed, let's process complex filters
        sanitized_filters = {}

        for key in args.filters:
            sanitized_filters[key.split('=')[0]] = key.split('=', 1)[1]

        return connection.get_all_reservations(None, sanitized_filters)


instance_counter = 0

for region in aws_regions:
    # requires special auth
    try:
        connection = boto.ec2.connect_to_region(region.name)
        reservations = getReservationsFromFilter(connection)

        for reservation in reservations:
            for instance in reservation.instances:
                if not instance.ip_address:
                    continue

                instance_counter += 1

                discovered_instances['#'].append(instance_counter)
                discovered_instances['IP Address'].append(instance.ip_address)

                for tag in instance.tags:
                    if tag not in discovered_instances:
                        discovered_instances[tag] = []

                    discovered_instances[tag].append(instance.tags[tag])
    except boto.exception.EC2ResponseError as e:
        print 'Received an error connecting to ' + region.name
         
            # possible for an instance to not have a tag, which could mess up the order of things in the array..

if len(discovered_instances['IP Address']) == 1:
    perform_ssh(discovered_instances['IP Address'][0])
else:
    print tabulate.tabulate(discovered_instances, headers="keys", tablefmt="grid")

    instance_choice = input('Enter the number of the instance to connect to: ')

    perform_ssh(discovered_instances['IP Address'][instance_choice - 1])
