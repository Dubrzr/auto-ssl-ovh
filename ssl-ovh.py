import os
import json
import ovh


conf = json.load(open('conf.json'))

client = ovh.Client(
    endpoint=conf['ovh_ids']['endpoint'],
    application_key=conf['ovh_ids']['app_key'],
    application_secret=conf['ovh_ids']['app_secret'],
    consumer_key=conf['ovh_ids']['consumer_key']
)

for domain in conf['domains']:
    print("Updating {}...".format(domain['url']))
    prfx =  '/domain/zone/{}'.format(domain['url'])
    
    entries_mappings = {client.get(prfx + '/record/{}'.format(record_id))['subDomain']: record_id for record_id in client.get(prfx + '/record')}
    print(entries_mappings)
