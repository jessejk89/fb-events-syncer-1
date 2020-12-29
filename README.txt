FOR DEVELOPMENT (without docker)

Install Python first (https://www.python.org/)
Create a file named config.py, see example.prod.config, with the following contents

####
fb_token = ""

fb_page_id = "200346284174326"
wp_base_url = "http://localhost:8000/wp-json/events_api/v1"
intervalHours = 4

resultsEmail = 'example@provider.nl'

emailServer = "smtp.gmail.com"
emailPort = 465
emailSender = 'example@gmail.com'
emailPassword = ''

logFile = '.\output.log'
####

Fill in your own token. For that you need a Facebook developers account and follow some steps (https://developers.facebook.com/docs/pages/access-tokens). A long-lived page access token works best.
The filled in id is from the xrnl facebook page but you can use your own or the id of a test page. Remember that the page id is linked to the token. The token grants access to a specific page.
Make sure that the xrnl website server behind <wp_base_url> is running and edit it if needed.
For sending emails you need to use an email address of your own and fill in the details. This is not required for the synchronization but it will give an error if e-mail fails.
The <resultsEmail> is the address to which the results will be emailed. The <emailServer>, <emailPort>, <emailSender>, <emailPassword> is used to send the email.

Before running a few python libraries are need, run
>pip install -r requirements.txt
Or
>pip install requests pytz

And make sure that the xrnl website is configured to accept event requests from your ip address, otherwise you will get a 401 Forbidden
To execute the script, run
>python start.py

On certain linux distributions the commands python and pip will not work so you need to use python3 and pip3 instead.

The script runs every <intervalHours> hours. This may be a too long interval for testing purposes so in that case you can open start.py with an editor and edit the following line
schedule.every(config.intervalHours).hours.do(synchronizeWithFile)

For example like this

schedule.every(5).minutes.do(synchronizeWithFile)

----

FOR STAGING / PRODUCTION

Copy the contents of 'example.prod.config.py' to a new file named 'prod.config.py', with the following contents

####
fb_token = ""

fb_page_id = "200346284174326"
wp_base_url = "http://172.22.0.101/wp-json/events_api/v1"
intervalHours = 4

resultsEmail = 'example@provider.nl'

emailServer = "smtp.gmail.com"
emailPort = 465
emailSender = 'xr.eventsyncer@gmail.com'
emailPassword = ''

logFile = '/var/log/fb-events-syncer/output.log'
####

The fb_token and emailPassword are secret, so get those first. Email settings are not mandatory for synchronization, but it will give errors when it can't send.
Fill in <resultsEmail> with the email address that needs to receive the synchronization results. The rest of the settings should already be in order.
The ip address 172.22.0.101 is a static ip address of the website's php server, inside a docker network with only the website and the sync script, which we will create next.
The variable <intervalHours> defines how often the script runs, so with 4 it runs every 4 hours.

Now run
>docker-compose up -d

This command creates and runs a container and creates the network.
After completion run
>docker network connect fb-events-syncer_xrnl-bridge <php_docker_id> --ip 172.22.0.101

This connects the website's php server container with network. The docker id can be obtained by running
>docker container list
