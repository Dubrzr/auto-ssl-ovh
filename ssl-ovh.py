import os
import json
import ovh
import ovh.exceptions   

from ACMEclient import ACMEclient
from dns_tools import OVHDns

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


class OvhClient:
    def __init__(self, endpoint, application_key, application_secret, consumer_key):
        self._client = ovh.Client(
            endpoint=conf['ovh_ids']['endpoint'],
            application_key=conf['ovh_ids']['app_key'],
            application_secret=conf['ovh_ids']['app_secret'],
            consumer_key=conf['ovh_ids']['consumer_key']
        )
        self._cache = {}

    @staticmethod
    def give_rights(zone):
        client = ovh.Client(
            endpoint=conf['ovh_ids']['endpoint'],
            application_key=conf['ovh_ids']['app_key'],
            application_secret=conf['ovh_ids']['app_secret']
        )
        ck = client.new_consumer_key_request()
        ck.add_recursive_rules(ovh.API_READ_WRITE, '/domain/zone/{}/*'.format(zone))
        validation = ck.request()

        print("Please visit {} to authenticate".format(validation['validationUrl']))
        input("and press Enter to continue...")

        print("Your 'consumerKey' is '{}'".format(validation['consumerKey']))

        return validation['consumerKey']


    def get_zone_mappings(self, zone, force_refresh=False):
        if not force_refresh and zone in self._cache:
            return self._cache[zone]

        prfx =  '/domain/zone/{}'.format(zone)

        entries_mappings = {}

        for record_id in self._client.get(prfx + '/record'):
            data = self._client.get(prfx + '/record/{}'.format(record_id))
            entries_mappings[data['subDomain']] = data

        self._cache[zone] = entries_mappings
        return self._cache[zone]

    def create_and_update_domains(self, domains):
        for zone in domains:
            print("Updating {} DNS entries...".format(zone['url']))
            prfx =  '/domain/zone/{}'.format(zone['url'])

            zone_mappings = self.get_zone_mappings(zone['url'])

            for dns_entry in zone['dns_entries']:
                subdomain = dns_entry['subDomain']
                dn = subdomain + '.' + zone['url']

                if subdomain not in zone_mappings:
                    # We create the entry
                    self.add_record(zone['url'], **dns_entry)

                    self._client.post(prfx + '/record', **dns_entry)
                    print("  -> Created DNS entry for {} ({})".format(dn, dns_entry))
                else:
                    data = zone_mappings[dns_entry['subDomain']]
                    if self.update_record(zone['url'], **dns_entry):
                        print("  -> Updated DNS entry for {} ({})".format(dn, dns_entry))

            self.refresh_zone(zone['url'])
            
    def refresh_zone(self, zone):
        self._client.post('/domain/zone/{}/refresh'.format(zone))
        print("Refreshed zone {}".format(zone))

    def add_record(self, zone, subDomain, fieldType, target, ttl=0):
        zone_mappings = self.get_zone_mappings(zone)

        if subDomain not in zone_mappings:
               # We create the entry
            self._client.post('/domain/zone/{}/record'.format(zone), 
                   subDomain=subDomain,
                   fieldType=fieldType,
                   target=target,
                   ttl=ttl)
        else:
            if zone_mappings[subDomain]['fieldType'] != fieldType:
                self.delete_record(zone, subDomain)
                return self.add_record(zone, subDomain, fieldType, target, ttl)

            record_id = zone_mappings[subDomain]['id']
            self._client.put('/domain/zone/{}/record/{}'.format(zone, record_id),
                   target=target,
                   ttl=ttl)

        self.refresh_zone(zone)

    def update_record(self, zone, subDomain, fieldType, target, ttl=0):
        # Returns True if it updated the record, False otherwise
        zone_mappings = self.get_zone_mappings(zone)

        if subDomain not in zone_mappings:
            raise Exception("SubDomain {} cannot be updated as it does not exists.".format(subDomain))

        s = zone_mappings[subDomain]
        if s['fieldType'] != fieldType:
            self.delete_record(zone, subDomain)
            self.add_record(zone, subDomain, fieldType, target, ttl)
            return True
        elif s['target'] != target or s['ttl'] != ttl:
            self._client.put('/domain/zone/{}/record/{}'.format(zone, s['id']),
                    subDomain=subDomain,
                    fieldType=fieldType,
                    target=target,
                    ttl=ttl)
            return True
        return False

        self.refresh_zone(zone)


    def delete_record(self, zone, subDomain):
        zone_mappings = self.get_zone_mappings(zone)

        if subDomain not in zone_mappings:
            return

        record_id = zone_mappings[subDomain]['id']
        self._client.delete('/domain/zone/{}/record/{}'.format(zone, record_id))

        del self._cache[zone][subDomain]

        self.refresh_zone(zone)



conf = json.load(open('conf.json'))

ovh_client = OvhClient(
                    endpoint=conf['ovh_ids']['endpoint'],
                    application_key=conf['ovh_ids']['app_key'],
                    application_secret=conf['ovh_ids']['app_secret'],
                    consumer_key=conf['ovh_ids']['consumer_key'])
#ovh_client.add_record('fgh.ovh', 'test.j1', 'TXT', '"zzzzz"')
ovh_client.create_and_update_domains(conf['domains'])

for certificate in conf['certificates']:
    acme = ACMEclient(certificate['cn'],
            dns_class=OVHDns(ovh_client),
            domain_alt_names=certificate['alt_names'],
            registration_recovery_email='contact@juliendubiel.net',
            account_key=None,
            bits=4096,
            digest='sha256',
            ACME_CHALLENGE_WAIT_PERIOD=60)

    certificate = acme.cert()
    certificate_key = acme.certificate_key
    account_key = acme.account_key

    with open('certificates/{}.crt'.format(certificate['name']), 'w') as certificate_file:
        certificate_file.write(certificate)

    with open('certificates/{}.key'.format(certificate['name']), 'w') as certificate_key_file:
        certificate_key_file.write(certificate_key)


    # 2. to renew a certificate:
    # with open('account_key.key', 'r') as account_key_file:
    #     account_key = account_key_file.read()

    # acme = sewer.Client(domain_name='example.com',
    #                       dns_class=dns_class,
    #                       account_key=account_key)
    # certificate = acme.renew()
    # certificate_key = acme.certificate_key