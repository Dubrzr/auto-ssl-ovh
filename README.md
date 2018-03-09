# Create Let's Encrypt free SSL certificates with OVH domains

* First `cp example.conf.json conf.json`
* Edit conf.json with all the needed parameters
* Run `pip install -r requirements.txt`
* Run `python ssl-ovh.py` when you are ready, this will create a `certificates` directory containing the created certificates specified in your `conf.json`
* Have fun!