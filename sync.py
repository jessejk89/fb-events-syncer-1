import requests
from datetime import datetime, timezone, timedelta
import time
import pytz
from hashlib import blake2b
import smtplib, ssl

import config
import converter
import utils
import db

fb_base_url = "https://graph.facebook.com"

fb_fields = "id, name, description,  end_time, event_times, place, start_time, cover, owner{name, emails, website}, is_online"

since_filter = None#"2020-09-30T12:00:00"
until_filter = None#"2020-09-23T21:00:00"

dryRun = False
fbToFile = False
outputFile = None
fbFromFile = False
inputFile = None

wpEventsByFacebookId = {}
fbEventsByFacebookId = {}
administrationByFacebookId = {}

createdEvents = []
updatedEvents = []
deletedEvents = []

# Because the ordering facebook uses is not completely clear, especially when using date filters and recurring events,
# we need another way to determine which events to check and which not.
# This function checks if the last end_time that it encounters is not more than 7 days in the past.
def isExpired(events):
    result = False
    for event in reversed(events):
        strEndTime = event.get('end_time')
        if strEndTime != None:
            endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
            if endTime < (datetime.now(timezone.utc) - timedelta(days=7)):
                result = True
                break
            else:
                result = False
                break

    return result


def makeFacebookRequest(url):
    print('Executing facebook request ' + url)
    response = requests.get(url)

    if response:
        print('Events request successful')
        print(response)
    else:
        print('Events request failed')
        print(response)
        return None

    return response

def getFacebookEventsFromFile(inputFile):
    print("Loading facebook events from file " + inputFile)
    with open(inputFile, 'r', encoding = 'utf-8') as eventsFile:
        data = eventsFile.read()

    return eval(data)

def getEventsFromFacebook():
    url = fb_base_url + '/' + config.fb_page_id + '/events?fields=' + fb_fields + '&access_token=' + config.fb_token

    # Disable date filtering for Facebok requests for now because they seem unreliable
    # start disable
    #if since_filter != None:
    #    url += ('&since='+ str(int(datetime.strptime(since_filter, '%Y-%m-%dT%H:%M:%S').timestamp())))
    #if until_filter != None:
    #    url += ('&until='+ str(int(datetime.strptime(until_filter, '%Y-%m-%dT%H:%M:%S').timestamp())))
    # end disable

    response = makeFacebookRequest(url)
    json = response.json()
    events = json.get('data')
    paging = json.get('paging')
    expired = isExpired(events)
    print('Received ' + str(len(events)) + ' events')

    while paging != None and paging.get('next') != None and not expired:
        response = makeFacebookRequest(json['paging']['next'])
        json = response.json()
        events1 = json.get('data')
        events = events + events1
        paging = json.get('paging')
        expired = isExpired(events1)
        print('Received ' + str(len(events1)) + ' events')
    else:
        if expired:
            print('Last event is expired')
        else:
            print('End of data')

    return events


def facebookEventExists(eventId):
    url = fb_base_url + '/' + str(eventId) + '?fields=id,name&access_token=' + config.fb_token
    response = requests.get(url)

    json = response.json()
    error = json.get('error')
    # Bad request 400 with error code 100 usually indicates that the event does not exist
    if (not response.ok) and error != None and error.get('code') != '100' and error.get('code') != 100:
        raise Exception(str(error))
    return response.ok

def getEventsFromWebsite():
    url = config.wp_base_url + '/events'
    if since_filter != None:
        sinceTime = datetime.strptime(since_filter, "%Y-%m-%dT%H:%M:%S")
        #start_timestamp = (sinceTime + sinceTime.utcoffset()).timestamp()
        url += ('?since_date=' + str(int(sinceTime.timestamp())))
        # TODO: make sure that timestamp is in local time
    if until_filter != None:
        untilTime = datetime.strptime(until_filter, "%Y-%m-%dT%H:%M:%S")
        #end_timestamp = (untilTime + untilTime.utcoffset()).timestamp()
        if since_filter:
            url += ('&until_date=' + str(int(untilTime.timestamp())))
        else:
            url += ('?until_date=' + str(int(untilTime.timestamp())))


    print('Executing website request ' + url)
    #response = requests.get(url, cookies = {'Cookie': config.wp_cookie})
    response = requests.get(url)
    if response:
        print('Events request successful')
        print(response)
    else:
        print('Events request failed')
        print(response)
        return None

    return response

def createNewSubEvent(event, parentEvent):
    newEvent = {
        'facebook_id': event['id'],
        'title': parentEvent['name'],
        'content': parentEvent['description']
    }

    administrationByFacebookId[event['id']] = {}

    if parentEvent.get('cover') != None:
        newEvent['picture_url'] = parentEvent['cover']['source']

    strStartTime = event.get('start_time')
    startTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
    administrationByFacebookId[event['id']]['start_time_object'] = startTime
    newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")

    strEndTime = event.get('end_time')
    if strEndTime != None:
        endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
        administrationByFacebookId[event['id']]['end_time_object'] = endTime
        newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
    else:
        #newEvent['end_date'] = None
        # make end_date equal start_date to prevent wordpress from falling back to current time
        endTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
        newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")

    converter.parseContent(parentEvent, newEvent)
    converter.parseCategoryInformation(parentEvent, newEvent)
    converter.parseLocationInformation(parentEvent, newEvent)
    converter.parseOwnerInformation(parentEvent, newEvent)
    converter.createFacebookHashValuesRecurringEvent(event, parentEvent, newEvent)

    return newEvent

# This method probably never gets called
def createNewEvent(event):
    newEvents = []
    newEvent = {
        'facebook_id': event['id'],
        'title': event['name']
    }

    administrationByFacebookId[event['id']] = {}

    if event.get('cover') != None:
        newEvent['picture_url'] = event['cover']['source']

    if event.get('event_times') != None: # we are dealing with a recurring event with multiple start- and endtimes and it's own facebook id
        for subEvent in event['event_times']:
            strStartTime = subEvent.get('start_time')
            startTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
            administrationByFacebookId[event['id']]['start_time_object'] = startTime

            newSubEvent = newEvent.copy()
            newSubEvent['facebook_id'] = subEvent['id']
            newSubEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")

            strEndTime = subEvent.get('end_time')
            if strEndTime != None:
                endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
                administrationByFacebookId[event['id']]['end_time_object'] = endTime
                newSubEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
            else:
                #newEvent['end_date'] = None
                # make end_date equal start_date to prevent wordpress from falling back to current time
                endTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
                newSubEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")

            newEvents.append(newSubEvent)
    else: # this is single event with only one start- and endtime
        strStartTime = event.get('start_time')
        startTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
        administrationByFacebookId[event['id']]['start_time_object'] = startTime
        newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")

        strEndTime = event.get('end_time')
        if strEndTime != None:
            endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
            administrationByFacebookId[event['id']]['end_time_object'] = endTime
            newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
        else:
            #newEvent['end_date'] = None
            # make end_date equal start_date to prevent wordpress from falling back to current time
            endTime = datetime.strptime(strStartTime, "%Y-%m-%dT%H:%M:%S%z")
            newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")

        newEvents.append(newEvent)

    # TODO: the code below should be above the newEvent.copy() statement so that all information is copied
    # Fortunately, this method appears not be executed for recurring events so there is no harm
    converter.parseContent(event, newEvent)
    converter.parseCategoryInformation(event, newEvent)
    converter.parseLocationInformation(event, newEvent)
    converter.parseOwnerInformation(event, newEvent)
    converter.createFacebookHashValues(event, newEvent)

    return newEvents

def createNewEvents(fbEvents):
    newEvents = []
    for event in fbEvents:
        # one facebook event can create one or multiple website events due to recurring events
        newEvents.extend(createNewEvent(event))

    return newEvents

def getEvent(id):
    url = config.wp_base_url + '/events/' + id
    print('Executing website request GET ' + url)
    #response = requests.get(url, cookies = {'Cookie': config.wp_cookie})
    response = requests.get(url)
    print(response)
    print('Text: ' + response.text)
    return response

def postEvent(event):
    url = config.wp_base_url + '/events'
    if dryRun:
        print('Executing in dry run mode. Ignoring website request POST ' + url)
        return "[V] " + time.time()
    print('Executing website request POST ' + url)
    #response = requests.post(url, data = event, cookies = {'Cookie': config.wp_cookie})
    response = requests.post(url, data = event)
    print(response)
    print('Text: ' + response.text)
    return response.text

def putEvent(event):
    url = config.wp_base_url + '/events/' + event['id']
    if dryRun:
        print('Executing in dry run mode. Ignoring website request POST ' + url)
        return "[V] " + time.time()
    print('Executing website request PUT ' + url)
    #response = requests.put(url, data = event, cookies = {'Cookie': config.wp_cookie})
    response = requests.put(url, data = event)
    print(response)
    print('Text: ' + response.text)
    return response.text

def eventIsUpdated(wpEvent, fbEvent, newEvent, subEvent = None, subEventThumbnailId = None, compareFields = ['name', 'description', 'start_time', 'end_time', 'place', 'owner', 'cover']):
    if len(compareFields) == 7:
        print("Doing an extensive comparison")
    else:
        print("Doing a superficial comparison")
    modified = False
    modifiedFields = []

    meta = wpEvent.get('meta')
    if meta != None:
        if 'name' in compareFields and meta.get('name_hash') != utils.bhash(fbEvent['name']):
            newEvent['title'] = fbEvent['name']
            newEvent['name_hash'] = utils.bhash(fbEvent.get('name'))
            modified = True
            modifiedFields.append('name')
            #print('UPDATED: "'+ wpEvent['title'] + ' - ' + fbEvent['name'] + '"')
            print('UPDATED: TITLE')
        if 'description' in compareFields and fbEvent.get('description') != None and meta.get('description_hash') != utils.bhash(fbEvent['description']):
            converter.parseContent(fbEvent, newEvent)
            #newEvent['content'] = fbEvent['description']
            newEvent['description_hash'] = utils.bhash(fbEvent.get('description'))
            modified = True
            modifiedFields.append('description')
            #print('UPDATED: "' + wpEvent['content'].encode('utf-8') + ' - ' + fbEvent['description'].encode('utf-8') + '"')
            print('UPDATED: DESCRIPTION')
        if subEvent != None:
            startTimeModified = False
            if meta.get('start_time_hash') != utils.bhash(subEvent.get('start_time')):
                startTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                newEvent['start_time_hash'] = utils.bhash(subEvent.get('start_time'))
                modified = True
                startTimeModified = True
                modifiedFields.append('start_time')
                print('UPDATED: "' + wpEvent['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
            strEndTime = subEvent.get('end_time')
            # When start_date is modified and end_date is None, end_date needs a correction
            if meta.get('end_time_hash') != utils.bhash(strEndTime) or (startTimeModified and strEndTime == None):
                if strEndTime != None:
                    endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
                    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                    newEvent['end_time_hash'] = utils.bhash(strEndTime)
                    modified = True
                    modifiedFields.append('end_time')
                    print('UPDATED: "' + wpEvent['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
                else:
                    #newEvent['end_date'] = None
                    # make end_date equal start_date to prevent wordpress from falling back to current time
                    endTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                    newEvent['end_time_hash'] = None
                    modified = True
                    modifiedFields.append('end_time')
        else:
            startTimeModified = False
            if meta.get('start_time_hash') != utils.bhash(fbEvent.get('start_time')):
                startTime = datetime.strptime(fbEvent.get('start_time'), "%Y-%m-%dT%H:%M:%S%z")
                newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                newEvent['start_time_hash'] = utils.bhash(fbEvent.get('start_time'))
                modified = True
                startTimeModified = True
                modifiedFields.append('start_time')
                print('UPDATED: "' + wpEvent['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
            strEndTime = fbEvent.get('end_time')
            # When start_date is modified and end_date is None, end_date needs a correction
            if meta.get('end_time_hash') != utils.bhash(strEndTime) or (startTimeModified and strEndTime == None):
                if strEndTime != None:
                    endTime = datetime.strptime(strEndTime, "%Y-%m-%dT%H:%M:%S%z")
                    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                    newEvent['end_time_hash'] = utils.bhash(fbEvent.get('end_time'))
                    modified = True
                    modifiedFields.append('end_time')
                    print('UPDATED: "' + wpEvent['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
                else:
                    #newEvent['end_date'] = None
                    # make end_date equal start_date to prevent wordpress from falling back to current time
                    endTime = datetime.strptime(fbEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                    newEvent['end_time_hash'] = None
                    modified = True
                    modifiedFields.append('end_time')
        if 'place' in compareFields and meta.get('place_hash') != utils.bhash(str(fbEvent.get('place'))):
            # for now add picture when there is none. We may need a way to detect if a picture has been changed
            if fbEvent.get('place') != None:
                converter.parseLocationInformation(fbEvent, newEvent)
                newEvent['place_hash'] = utils.bhash(str(fbEvent.get('place')))
                modified = True
                modifiedFields.append('place')
                print('UPDATED PLACE')
        if 'owner' in compareFields and meta.get('owner_hash') != utils.bhash(str(fbEvent.get('owner'))):
            # for now add picture when there is none. We may need a way to detect if a picture has been changed
            if fbEvent.get('owner') != None:
                converter.parseOwnerInformation(fbEvent, newEvent)
                newEvent['owner_hash'] = utils.bhash(str(fbEvent.get('owner')))
                modified = True
                modifiedFields.append('owner')
                print('UPDATED OWNER')
        # TODO: would be nice if I don't have to compare the cover (and do an HTTP-request) for all recurring subevents when I already know it's changed
        # Those requests make the script more slow
        if 'cover' in compareFields and fbEvent.get('cover') != None and fbEvent['cover'].get('source') != None:
            response = requests.get(fbEvent['cover']['source'])
            hash = utils.bhash(str(response.content))
            if meta.get('_cover_bytes_hash') != hash:
                if subEventThumbnailId != None:
                    newEvent['thumbnail_id'] = subEventThumbnailId
                else:
                    newEvent['picture_url'] = fbEvent['cover'].get('source')
                newEvent['_cover_bytes_hash'] = hash
                modified = True
                modifiedFields.append('cover')
                print('UPDATED COVER BYTES')
            else:
                print('cover bytes are not changed')
        # if meta.get('cover_hash') != utils.bhash(str(fbEvent.get('cover'))):
        #     if fbEvent.get('cover') != None:
        #         if subEventThumbnailId != None:
        #             newEvent['thumbnail_id'] = subEventThumbnailId
        #         else:
        #             newEvent['picture_url'] = fbEvent['cover'].get('source')
        #         newEvent['cover_hash'] = utils.bhash(str(fbEvent.get('cover')))
        #         modified = True
        #         print('UPDATED COVER')

        #return modified
        return modifiedFields

def compareAndSync(fbEvents):
    for fbEvent in fbEvents:
        wpEvent = wpEventsByFacebookId.get(fbEvent['id'])
        if wpEvent != None:
            print("Match found for facebook_id " + fbEvent['id'])
            # compare and update if necessary
            newEvent = {'id': wpEvent['id']}

            #TODO: compare all fields and check if event is now a recurring event
            modFields = eventIsUpdated(wpEvent, fbEvent, newEvent)
            if len(modFields) > 0:
                putEvent(newEvent)
                wpEvent['facebook_id'] = fbEvent['id']
                updatedEvents.append(wpEvent)
            else:
                print("No updates detected for main event")
        else:
            print("No match for facebook_id..." + fbEvent['id'])
            subEventThumbnailId = None
            if fbEvent.get('event_times') != None:
                print('...trying subevents')
                modifiedFields = ['name', 'description', 'start_time', 'end_time', 'place', 'owner', 'cover']
                for subEvent in fbEvent['event_times']:
                    wpEvent2 = wpEventsByFacebookId.get(subEvent['id'])
                    if wpEvent2 != None:
                        print("Match found for facebook_id " + subEvent['id'])
                        # compare and update if necessary
                        # make sure to compare parent event's properties
                        newEvent = {'id': wpEvent2['id']}
                        modified2 = False

                        modifiedFields = eventIsUpdated(wpEvent2, fbEvent, newEvent, subEvent, subEventThumbnailId, modifiedFields)
                        if len(modifiedFields) > 0:
                            eventId = putEvent(newEvent)
                            wpEvent2['facebook_id'] = subEvent['id']
                            updatedEvents.append(wpEvent2)
                            if subEventThumbnailId == None:
                                print("Thumbnail does not exist yet for updated event " + eventId)
                                serverEvent = getEvent(eventId).json()
                                subEventThumbnailId = serverEvent.get('meta').get('_thumbnail_id')
                        else:
                            print("No updates detected for recurring subevent")
                    else:
                        print("No match for subevent facebook_id " + subEvent['id'])
                        print("Creating new event")

                        if subEventThumbnailId == None:
                            print("Thumbnail does not exist yet")
                            convertedEvent = createNewSubEvent(subEvent, fbEvent)
                            eventId = postEvent(convertedEvent)
                            convertedEvent['wordpress_id'] = eventId
                            createdEvents.append(convertedEvent)
                            serverEvent = getEvent(eventId).json()
                            subEventThumbnailId = serverEvent.get('meta').get('_thumbnail_id')
                        else:
                            print("Thumbnail found " + subEventThumbnailId)
                            convertedEvent = createNewSubEvent(subEvent, fbEvent)
                            convertedEvent.pop('picture_url', None)
                            convertedEvent['thumbnail_id'] = subEventThumbnailId
                            #print(str(convertedEvent))
                            wordpressId = postEvent(convertedEvent)
                            convertedEvent['wordpress_id'] = wordpressId
                            createdEvents.append(convertedEvent)
            else:
                print('No match and no subevents, creating new event')
                convertedEvents = createNewEvent(fbEvent)
                for convertedEvent in convertedEvents:
                    wordpressId = postEvent(convertedEvent)
                    convertedEvent['wordpress_id'] = wordpressId
                    createdEvents.append(convertedEvent)

def detectCancelledEvents(wpEvents):
    for wpEvent in wpEvents:
        meta = wpEvent.get('meta')
        if meta != None and meta.get('facebook_id'):
            fbEvent = fbEventsByFacebookId.get(meta['facebook_id'])
            if fbEvent == None and not facebookEventExists(meta['facebook_id']):
                print('No facebook event for wordpress event with facebook_id ' + meta['facebook_id'])
                print('deleting event...')
                wpEvent['post_status'] = 'trash'
                newEvent = {'id': wpEvent['id'], 'post_status': 'trash'}
                print("CANCELLED EVENT FOUND " + wpEvent['title'])
                putEvent(newEvent)
                wpEvent['facebook_id'] = meta['facebook_id']
                deletedEvents.append(wpEvent)

def writeEventsToFile(events, filename):
    file  = open(filename, 'w', encoding='utf-8')
    file.write(events)
    file.close()

def createMessageBody():
    emailBody = ''

    if len(createdEvents) == 0 and len(updatedEvents) == 0 and len(deletedEvents) == 0:
        emailBody = 'No changes were detected during event synchronisation'
    else:
        emailBody += 'Created events: ' + str(len(createdEvents)) + '\n'
        for ce in createdEvents:
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(ce.get('wordpress_id')) + '&action=edit&lang=nl')
            emailBody = emailBody + ('* ' + ce.get('title') + ' | Wordpress: [' + str(ce.get('wordpress_id')) + '](' + url + ') | Facebook: [' + str(ce.get('facebook_id')) + '](https://www.facebook.com/events/' + str(ce.get('facebook_id')) + ')\n')

        emailBody += '\n\nUpdated events: ' + str(len(updatedEvents)) + '\n'
        for ue in updatedEvents:
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(ue.get('id')) + '&action=edit&lang=nl')
            emailBody = emailBody + ('* ' + ue.get('title') + ' | Wordpress: [' + str(ue.get('id')) + ' ](' + url + ') | Facebook: [' + str(ue.get('facebook_id')) + '](https://www.facebook.com/events/' + str(ue.get('facebook_id')) + ')\n')

        emailBody += '\n\nTrashed events: ' + str(len(deletedEvents)) + '\n'
        for de in deletedEvents:
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(de.get('id')) + '&action=edit&lang=nl')
            emailBody = emailBody + ('* ' + de.get('title') + ' | Wordpress: [' + str(de.get('id')) + ' ](' + url + ') | Facebook: [' + str(de.get('facebook_id')) + '](https://www.facebook.com/events/' + str(de.get('facebook_id')) + ')\n')

    return emailBody

def sendEmail():
    print("Sending e-mail to " + str(config.resultsEmail))
    emailBody = 'Subject: Facebook event synchronization results\n\n'
    emailBody += createMessageBody()

    try:
        # Create a secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(config.emailServer, config.emailPort, context=context) as server:
            server.login(config.emailSender, config.emailPassword)
            server.sendmail(config.emailSender, config.resultsEmail, emailBody.encode('utf-8'))
        print("Successfully sent email")
    except smtplib.SMTPException as e:
        print("Error: unable to send email")
        if hasattr(e, 'message'):
            print(e.message)
        else:
            print(e)

def postToMattermostChannel(channelId, message):
    data = {"channel_id": channelId, "message": message}
    headers = {'Authorization': config.mattermostToken}
    response = requests.post(config.mattermostBaseUrl + 'api/v4/posts', headers=headers, json=data)
    if response != None and response.ok:
        print("Mattermost post succesful, response:" + str(response))
    else:
        print("Error posting to mattermost")
        print("Mattermost post response:" + str(response))
    return response

def postInMattermost():
    print("Posting message in Mattermost to " + str(config.mattermostChannelId))
    emailBody = createMessageBody()# + '\n```----```\n'
    postToMattermostChannel(config.mattermostChannelId, emailBody)


def postInMattermostSeperate():
    print("Posting messages in Mattermost to " + str(config.mattermostChannelId))
    generalMessage = ''
    changesDetected = False

    if len(createdEvents) == 0 and len(updatedEvents) == 0 and len(deletedEvents) == 0:
        generalMessage = 'Event synchronization round complete: no changes detected\n'
    else:
        changesDetected = True
        generalMessage = 'Event synchronization round complete\n'
        generalMessage += 'Created events: ' + str(len(createdEvents)) + '\n'
        for ce in createdEvents:
            #TODO: replace correct api version
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(ce.get('wordpress_id')) + '&action=edit&lang=nl')
            text = 'A new event was created' + '\n'
            organizer = ce.get('organizer_name')

            syncerString = ''
            endDateObject = administrationByFacebookId[ce.get('facebook_id')].get('end_time_object')
            startDateObject = administrationByFacebookId[ce.get('facebook_id')].get('start_time_object')

            # check if event has passed; if yes then there is no need to notify users with a tag
            if (endDateObject != None and endDateObject > datetime.now(timezone.utc)) or (endDateObject == None and startDateObject > (datetime.now(timezone.utc) - timedelta(days=1))):
                syncerString = formatSyncers(organizer)

            if organizer != None:
                text = syncerString + ' A new event was created organized by ' + organizer + '\n'

            text += ('* ' + ce.get('title') + ' | Wordpress: [' + str(ce.get('wordpress_id')) + '](' + url + ') | Facebook: [' + str(ce.get('facebook_id')) + '](https://www.facebook.com/events/' + str(ce.get('facebook_id')) + ')\n')
            postToMattermostChannel(config.mattermostChannelId, text)

        generalMessage += '\n\nUpdated events: ' + str(len(updatedEvents)) + '\n'
        for ue in updatedEvents:
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(ue.get('id')) + '&action=edit&lang=nl')
            text = 'An existing event was updated \n'
            organizer = ue.get('meta').get('organizer_name')

            syncerString = ''
            endDateObject = administrationByFacebookId[ce.get('facebook_id')].get('end_time_object')
            startDateObject = administrationByFacebookId[ce.get('facebook_id')].get('start_time_object')

            # check if event has passed; if yes then there is no need to notify users with a tag
            if (endDateObject != None and endDateObject > datetime.now(timezone.utc)) or (endDateObject == None and startDateObject > (datetime.now(timezone.utc) - timedelta(days=1))):
                syncerString = formatSyncers(organizer)

            if organizer != None:
                text = syncerString + ' An existing event organized by ' + organizer + ' was updated \n'

            text = text + ('* ' + ue.get('title') + ' | Wordpress: [' + str(ue.get('id')) + ' ](' + url + ') | Facebook: [' + str(ue.get('facebook_id')) + '](https://www.facebook.com/events/' + str(ue.get('facebook_id')) + ')\n')
            postToMattermostChannel(config.mattermostChannelId, text)

        generalMessage += '\n\nTrashed events: ' + str(len(deletedEvents)) + '\n'
        for de in deletedEvents:
            url = config.wp_base_url.replace('wp-json/events_api/v1', 'wp/wp-admin/post.php?post=' + str(de.get('id')) + '&action=edit&lang=nl')
            text = 'An existing event was trashed\n'
            organizer = de.get('meta').get('organizer_name')

            syncerString = ''
            endDateObject = administrationByFacebookId[ce.get('facebook_id')].get('end_time_object')
            startDateObject = administrationByFacebookId[ce.get('facebook_id')].get('start_time_object')

            # check if event has passed; if yes then there is no need to notify users with a tag
            if (endDateObject != None and endDateObject > datetime.now(timezone.utc)) or (endDateObject == None and startDateObject > (datetime.now(timezone.utc) - timedelta(days=1))):
                syncerString = formatSyncers(organizer)

            if organizer != None:
                text = syncerString + ' An existing event organized by ' + organizer + ' was trashed \n'
            text = text + ('* ' + de.get('title') + ' | Wordpress: [' + str(de.get('id')) + ' ](' + url + ') | Facebook: [' + str(de.get('facebook_id')) + '](https://www.facebook.com/events/' + str(de.get('facebook_id')) + ')\n')
            postToMattermostChannel(config.mattermostChannelId, text)

    if changesDetected:
        postToMattermostChannel(config.mattermostChannelId, '***')
    postToMattermostChannel(config.mattermostChannelId, generalMessage)

def formatSyncers(organizer):
    syncerString = ''
    if organizer != None:
        syncers = db.syncersByOrganizerName.get(organizer)
        if syncers != None:
            for s in syncers:
                syncerString += ('@' + s + ' ')
        else:
            syncerString = ''
            for s in db.defaultSyncers:
                syncerString += ('@' + s + ' ')
    return syncerString

def init(_dryRun, _fbToFile, _outputFile, _fbFromFile, _inputFile):
    global dryRun, fbToFile, outputFile, fbFromFile, inputFile
    global wpEventsByFacebookId, fbEventsByFacebookId, createdEvents, updatedEvents, deletedEvents

    # Set command line arguments
    dryRun = _dryRun
    fbToFile = _fbToFile
    outputFile = _outputFile
    fbFromFile = _fbFromFile
    inputFile = _inputFile

    wpEventsByFacebookId = {}
    fbEventsByFacebookId = {}

    createdEvents = []
    updatedEvents = []
    deletedEvents = []

def synchronize(dryRun, fbToFile, outputFile, fbFromFile, inputFile):
    init(dryRun, fbToFile, outputFile, fbFromFile, inputFile)
    print('\n')
    print('[START SYNCHRONISATION] ' + str(datetime.now()))
    # prepare hash table with website events for easy, fast access
    wpEvents = getEventsFromWebsite()
    if wpEvents == None:
        print('Synchronisation failed, returning')
        return

    dict1 = wpEvents.json()
    for item in dict1:
        #print('WP Event found; id: ' + item['id'] + '; title: ' + item['title'])
        if item.get('meta') != None and item['meta'].get('facebook_id') != None:
            fbId = item['meta']['facebook_id']
            wpEventsByFacebookId[fbId] = item

    # print(str(wpEventsByFacebookId))
    # get facebook events

    if fbFromFile:
        events = getFacebookEventsFromFile(inputFile)
        print("EVENTS COUNT " + str(len(events)))
    else:
        events = getEventsFromFacebook()

    if events == None:
        print('Synchronisation failed, returning')
        return

    if fbToFile:
        writeEventsToFile(str(events), outputFile)
        print('Writing ' + str(len(events)) + ' events to file ' + outputFile)

    for item in events:
        print('Event found; id: ' + item['id'] + '; name: ' + item['name'] + '; time: ' + item['start_time'])
        if item.get('place') != None and item['place'].get('name') != None:
            print('--place: ' + item['place']['name'] )
        fbEventsByFacebookId[item['id']] = item
        if item.get('event_times') != None:
            for subItem in item['event_times']:
                print('\tSubevent found, id: ' + subItem['id'])
                fbEventsByFacebookId[subItem['id']] = subItem

     # newEvents = reversed(createNewEvents(dict2))

    compareAndSync(events)
    # try:
    #     detectCancelledEvents(dict1)
    # except BaseException as e:
    #     print('An error occured when detecting cancelled events')
    #     print(e)

    print('Importing facebook events done')
    try:
        if config.emailResult:
            sendEmail()
        if config.postInMattermost:
            postInMattermostSeperate()
    finally:
        print('[END OF SYNCHRONISATION] ' + str(datetime.now()))
        print('\n')

def test():
    print('[START TEST] ' + str(datetime.now()))
    print("Executing test code...")
    print('[END OF TEST] ' + str(datetime.now()))
    print('\n')
