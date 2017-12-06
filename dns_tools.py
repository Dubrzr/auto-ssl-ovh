from structlog import get_logger
from datetime import datetime, timedelta
import dns.resolver
import time
import sys

my_resolver = dns.resolver.Resolver()

my_resolver.nameservers = ['10.176.208.153']


class BaseDns(object):
    def __init__(self):
        self.dns_provider_name = None
        if self.dns_provider_name is None:
            raise ValueError('The class attribute dns_provider_name ought to be defined.')

    def create_dns_record(self, domain_name, base64_of_acme_keyauthorization):
        raise NotImplementedError('create_dns_record method must be implemented.')

    def delete_dns_record(self, domain_name, base64_of_acme_keyauthorization):
        raise NotImplementedError('delete_dns_record method must be implemented.')


class OVHDns(BaseDns):

    def __init__(self, ovh_client):
        self.dns_provider_name = 'OVH'
        self.ovh_client = ovh_client

    def create_dns_record(self, domain_name, base64_of_acme_keyauthorization):
        s = domain_name.split('.')
        zone = '.'.join(s[-2:])
        subDomain = '_acme-challenge.' + '.'.join(s[:-2])
        target = '"{}"'.format(base64_of_acme_keyauthorization)
        try:
            self.ovh_client.delete_record(zone, subDomain)
        except:
            pass
        self.ovh_client.add_record(zone, subDomain, fieldType='TXT', target=target)
        print("Added DNS record {}|{}|{}".format(subDomain, 'TXT', target))

        print("NS lookups until {} DNS record is found".format(subDomain + '.' + zone), end='')
        sys.stdout.flush()

        timeout = 1200
        t = datetime.now()
        while True:
            try:
                answers = my_resolver.query(subDomain + '.' + zone, 'TXT')
            except dns.resolver.NXDOMAIN:
                answers = []
            if len(answers)> 0:
                print(answers[0])
            if len(answers) > 0 and answers[0] == target:
                break
            if timedelta.total_seconds(datetime.now() - t) > timeout:
                raise Exception("DNS record is still unupdated after {} seconds. Exiting...".format(timeout))
            time.sleep(5)
            print('.', end='')
            sys.stdout.flush()
        print(' Found!')


    def delete_dns_record(self, domain_name, base64_of_acme_keyauthorization):
        s = domain_name.split('.')
        zone = '.'.join(s[-2:])
        subDomain = '.'.join(s[:-2])
        self.ovh_client.delete_record(zone, '_acme-challenge.' + subDomain)