Create a file named config.py with the following contents:

fb_token = "TOKEN_EXAMPLE_CONTENT"

Fill in your own token. For that you need a Facebook developers account. For a token that gives access to the XRNL Facebook, you need to ask the Event Synchronisation Team.

Because the events REST API only accepts requests from 127.0.0.1, the files sync.py and config.py have to be copied to the machine that runs the XRNL website.
For developing purposes, this is inside the docker image. If everything is in order the /var/www/html folder of the website server mounts your local machine's XRNL website folder.
Open a terminal to the extinction-rebellion-nl_php server and execute:

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
