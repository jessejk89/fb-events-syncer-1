For development

Create a file named config.py, see example.prod.config, with the following contents

fb_token = ""

fb_page_id = "200346284174326"
wp_base_url = "http://172.22.0.2/wp-json/events_api/v1"

resultsEmail = 'example@provider.nl'

emailServer = "smtp.gmail.com"
emailPort = 465
emailSender = 'xr.eventsyncer@gmail.com'
emailPassword = ''

logFile = '/var/log/fb-events-syncer/output.log'


Fill in your own token. For that you need a Facebook developers account. For a token that gives access to the XRNL Facebook, you need to ask the Event Synchronisation Team.


>cd /var/www/html/

Locate the copied files and goto the top of the sync.py file and check all settings are in order. Pay special attention to the wp_base_url variable.
Make sure that the ip address 127.0.0.1 is used and no port is specified. Locally, php runs on port 80 and NOT on port 8000

wp_base_url = "http://127.0.0.1/wp-json/events_api/v1"

fb_page_id is the id of the XRNL facebook page, it should already be filled in correctly.

fb_page_id = "200346284174326"

To execute the script, run
>python3 sync.py

If the docker image is not setup for running the synchronisation script, you need to execute the following first:

>apt-get update
>apt-get install python3 python3-pip
>pip3 install requests
>pip3 install pytz
