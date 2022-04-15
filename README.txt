FOR DEVELOPMENT (without docker)

Install Python first (https://www.python.org/)
Create a file named config.py, see example.prod.config, with the following contents

####
fb_token = ""

fb_page_id = "200346284174326"
wp_base_url = "http://localhost:8000/wp-json/events_api/v1"
intervalHours = 4

resultsEmail = 'example@provider.nl'

emailResult = False
emailServer = "smtp.gmail.com"
emailPort = 465
emailSender = 'example@gmail.com'
emailPassword = ''

postInMattermost = False
mattermostBaseUrl = 'https://organise.earth/'
mattermostChannelId = ''
mattermostToken = ''

logFile = '.\output.log'
####

Fill in your own token. For that you need a Facebook developers account and follow some steps (https://developers.facebook.com/docs/pages/access-tokens). A long-lived page access token works best.
The filled in id is from the xrnl facebook page but you can use your own or the id of a test page. Remember that the page id is linked to the token. The token grants access to a specific page.
Make sure that the xrnl website server behind <wp_base_url> is running and edit it if needed.
For sending emails you need to use an email address of your own and fill in the details. You can enable or disable the sending of result emails by setting emailResult to True or False respectively.
The <resultsEmail> is the address to which the results will be emailed. The <emailServer>, <emailPort>, <emailSender>, <emailPassword> is used to send the email.
Results can also be posted in mattermost, to enable this set postInMattermost to True. The channel id can be seen under View Info of the mattermost channel.
This link explains how to acquire a mattermost token: https://api.mattermost.com/#tag/authentication

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


# Command line
The script can be started as follows
>python start.py

Certain behaviour can be manipulated through the use of parameters.

A dry run only performs a retrieval of facebook and wordpress events and compares them, it does not post anything to the wordpress website
> python start.py --dry-run

Events can be written to a file in json format like this
>python start.py --fb-to-file events.json

The above ability to write to a file can be very usefull for testing purposes. It can be combined with a dry run. To use a file as input source, the fb-from-file parameter can be used, it then uses the file as input source INSTEAD of facebook.
>python start.py --fb-from-file events.json


----

FOR STAGING / PRODUCTION

Copy the contents of 'example.prod.config.py' to a new file named 'prod.config.py', with the following contents

####
fb_token = ""

fb_page_id = "200346284174326"
wp_base_url = "http://development.extinctionrebellion.nl/wp-json/events_api/v1"
intervalHours = 4

resultsEmail = 'example@provider.nl'

emailResult = False
emailServer = "smtp.gmail.com"
emailPort = 465
emailSender = 'xr.eventsyncer@gmail.com'
emailPassword = ''

postInMattermost = True
mattermostBaseUrl = 'https://organise.earth/'
mattermostChannelId = 't16jxzgts78j3qqxrtrs79ps7a'
mattermostToken = ''

logFile = '/var/log/fb-events-syncer/output.log'
####

The fb_token, emailPassword and mattermostToken are secret, so get those first. Email and mattermost  settings are not mandatory. You can disable them by settings emailResult and/or postInMattermost to False
For information on howto get a Facebook token see https://developers.facebook.com/docs/pages/access-tokens
For information on howto get a Mattermost token see https://api.mattermost.com/#tag/authentication
Fill in <resultsEmail> with the email address that needs to receive the synchronization results. The rest of the settings should already be in order.
The variable <intervalHours> defines how often the script runs, so with 4 it runs every 4 hours.

Now run
>docker-compose up -d

This command creates and runs a container. If configuration is in order that's all.
