import requests
from datetime import datetime, timezone
import pytz
from hashlib import blake2b

import config
import converter

fb_base_url = "https://graph.facebook.com"
fb_page_id = "111101134055001"
#page_id = "115563666940099"
fb_fields = "id, name, category, attending_count, description,  end_time, event_times, place,start_time, cover, owner{name, emails, phone, website}"

wp_base_url = "http://localhost:8000/wp-json/events_api/v1"
since_filter = "2020-09-30T12:00:00"
until_filter = None#"2020-09-23T21:00:00"

wpEventsByFacebookId = {}

def getEventsFromFacebook():
    url = fb_base_url + '/' + fb_page_id + '/events?fields=' + fb_fields + '&access_token=' + config.fb_token
    if since_filter != None:
        url += ('&since='+ str(int(datetime.strptime(since_filter, '%Y-%m-%dT%H:%M:%S').timestamp())))
    if until_filter != None:
        url += ('&until='+ str(int(datetime.strptime(until_filter, '%Y-%m-%dT%H:%M:%S').timestamp())))

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

def getEventsFromWebsite():
    url = wp_base_url + '/events'
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
    response = requests.get(url, cookies = {'Cookie': config.wp_cookie})
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

    if parentEvent.get('cover') != None:
        newEvent['picture_url'] = parentEvent['cover']['source']

    startTime = datetime.strptime(event['start_time'], "%Y-%m-%dT%H:%M:%S%z")
    endTime = datetime.strptime(event['end_time'], "%Y-%m-%dT%H:%M:%S%z")
    newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")

    converter.parseCategoryInformation(parentEvent, newEvent)
    converter.parseLocationInformation(parentEvent, newEvent)
    converter.parseOwnerInformation(parentEvent, newEvent)
    converter.createFacebookHashValuesRecurringEvent(event, parentEvent, newEvent)

    return newEvent

def createNewEvent(event):
    newEvents = []
    newEvent = {
        'facebook_id': event['id'],
        'title': event['name'],
        'content': event['description']
    }

    if event.get('cover') != None:
        newEvent['picture_url'] = event['cover']['source']

    if event.get('event_times') != None: # we are dealing with a recurring event with multiple start- and endtimes and it's own facebook id
        for subEvent in event['event_times']:
            startTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
            endTime = datetime.strptime(subEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")

            newSubEvent = newEvent.copy()
            newSubEvent['facebook_id'] = subEvent['id']
            newSubEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
            newSubEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
            newEvents.append(newSubEvent)
    else: # this is single event with only one start- and endtime
        startTime = datetime.strptime(event['start_time'], "%Y-%m-%dT%H:%M:%S%z")
        endTime = datetime.strptime(event['end_time'], "%Y-%m-%dT%H:%M:%S%z")
        newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
        newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
        newEvents.append(newEvent)

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
    url = wp_base_url + '/events/' + id
    print('Executing website request GET ' + url)
    response = requests.get(url, cookies = {'Cookie': config.wp_cookie})
    print(response)
    print('Text: ' + response.text)
    return response

def postEvent(event):
    url = wp_base_url + '/events'
    print('Executing website request POST ' + url)
    response = requests.post(url, data = event, cookies = {'Cookie': config.wp_cookie})
    print(response)
    print('Text: ' + response.text)
    return response.text

def putEvent(event):
    url = wp_base_url + '/events/' + event['id']
    print('Executing website request PUT ' + url)
    response = requests.put(url, data = event, cookies = {'Cookie': config.wp_cookie})
    print(response)
    print('Text: ' + response.text)
    return response.text

def bhash(content):
    return blake2b(bytes(content, 'utf-8')).hexdigest()

def eventIsUpdated(wpEvent, fbEvent, newEvent, subEvent):
    modified = False

    meta = wpEvent.get('meta')
    if meta != None:
        if meta.get('name_hash') != bhash(fbEvent['name']):
            newEvent['title'] = fbEvent['name']
            newEvent['name_hash'] = bhash(fbEvent.get('name'))
            modified = True
            #print('UPDATED: "'+ wpEvent['title'] + ' - ' + fbEvent['name'] + '"')
            print('UPDATED: "'+ str(meta.get('name_hash')) + '" - "' + str(bhash(fbEvent['name'])) + '"')
        if meta.get('description_hash') != bhash(fbEvent['description']):
            newEvent['content'] = fbEvent['description']
            newEvent['description_hash'] = bhash(fbEvent.get('description'))
            modified = True
            print('UPDATED: "' + wpEvent['content'] + ' - ' + fbEvent['description'] + '"')
        if subEvent != None:
            if meta.get('start_time_hash') != bhash(subEvent['start_time']):
                startTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                newEvent['start_time_hash'] = bhash(subEvent.get('start_time'))
                modified = True
                print('UPDATED: "' + wpEvent['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
            if meta.get('end_time_hash') != bhash(subEvent['end_time']):
                endTime = datetime.strptime(subEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")
                newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                newEvent['end_time_hash'] = bhash(subEvent.get('end_time'))
                modified = True
                print('UPDATED: "' + wpEvent['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
        else:
            if meta.get('start_time_hash') != bhash(fbEvent['start_time']):
                startTime = datetime.strptime(fbEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                newEvent['start_time_hash'] = bhash(fbEvent.get('start_time'))
                modified = True
                print('UPDATED: "' + wpEvent['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
            if meta.get('end_time_hash') != bhash(fbEvent['end_time']):
                endTime = datetime.strptime(fbEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")
                newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                newEvent['end_time_hash'] = bhash(fbEvent.get('end_time'))
                modified = True
                print('UPDATED: "' + wpEvent['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
        if meta.get('place_hash') != bhash(str(fbEvent.get('place'))):
            # for now add picture when there is none. We may need a way to detect if a picture has been changed
            if fbEvent.get('place') != None:
                converter.parseLocationInformation(fbEvent, newEvent)
                newEvent['place_hash'] = bhash(str(fbEvent.get('place')))
                modified = True
                print('UPDATED PLACE')
        if meta.get('owner_hash') != bhash(str(fbEvent.get('owner'))):
            # for now add picture when there is none. We may need a way to detect if a picture has been changed
            if fbEvent.get('owner') != None:
                converter.parseOwnerInformation(fbEvent, newEvent)
                newEvent['owner_hash'] = bhash(str(fbEvent.get('owner')))
                modified = True
                print('UPDATED OWNER')
        if meta.get('cover_hash') != bhash(str(fbEvent.get('cover'))):
            # for now add picture when there is none. We may need a way to detect if a picture has been changed
            if fbEvent.get('cover') != None:
                newEvent['picture_url'] = fbEvent['cover']['source']
                newEvent['cover_hash'] = bhash(str(fbEvent.get('cover')))
                modified = True
                print('UPDATED COVER')

        return modified

def compare(fbEvents):
    for fbEvent in fbEvents:
        wpEvent = wpEventsByFacebookId.get(fbEvent['id'])
        if wpEvent != None:
            print("Match found for facebook_id " + fbEvent['id'])
            # compare and update if necessary
            newEvent = {'id': wpEvent['id']}

            #TODO: compare all fields and check if event is now a recurring event
            if eventIsUpdated(wpEvent, fbEvent, newEvent, None):
                putEvent(newEvent)
            else:
                print("No updates detected for main event")
        else:
            print("No match for facebook_id..." + fbEvent['id'])
            subEventThumbnailId = None
            if fbEvent.get('event_times') != None:
                print('...trying subevents')
                for subEvent in fbEvent['event_times']:
                    wpEvent2 = wpEventsByFacebookId.get(subEvent['id'])
                    if wpEvent2 != None:
                        print("Match found for facebook_id " + subEvent['id'])
                        # compare and update if necessary
                        # make sure to compare parent event's properties
                        newEvent = {'id': wpEvent2['id']}
                        modified2 = False

                        #TODO: compare all fields and check if event is now a recurring event
                        if eventIsUpdated(wpEvent2, fbEvent, newEvent, subEvent):
                            putEvent(newEvent)
                        else:
                            print("No updates detected for recurring subevent")
                    else:
                        print("No match for subevent facebook_id " + subEvent['id'])
                        print("Creating new event")

                        if subEventThumbnailId == None:
                            print("Thumbnail does not exist yet")
                            convertedEvent = createNewSubEvent(subEvent, fbEvent)
                            eventId = postEvent(convertedEvent)
                            serverEvent = getEvent(eventId).json()
                            subEventThumbnailId = serverEvent.get('meta').get('_thumbnail_id')
                        else:
                            print("Thumbnail found " + subEventThumbnailId)
                            convertedEvent = createNewSubEvent(subEvent, fbEvent)
                            convertedEvent.pop('picture_url', None)
                            convertedEvent['thumbnail_id'] = subEventThumbnailId
                            print(str(convertedEvent))
                            postEvent(convertedEvent)
            else:
                print('No match and no subevents, creating new event')
                convertedEvents = createNewEvent(fbEvent)
                for convertedEvent in convertedEvents:
                    postEvent(convertedEvent)

def writeEventsToFile(events, filename):
    file  = open(filename, 'w', encoding='utf-8')
    file.write(events)
    file.close()

def execute():
    events = getEventsFromFacebook()
    if events == None:
        return
    writeEventsToFile(events.text, 'fb_events.txt')
    dict1 = events.json()['data']
    print(str(len(dict1)) + ' events counted')

    for item in dict1:
        print('Event found; id: ' + item['id'] + '; name: ' + item['name'] + '; place: ' + item['place']['name'] + '; time: ' + item['start_time'])

def execute2():
    events = getEventsFromWebsite()
    if events == None:
        return
    writeEventsToFile(events.text, 'wp_events.txt')
    dict1 = events.json()
    print(str(len(dict1)) + ' events counted')

    for item in dict1:
        s = 'Event found; id: ' + item['id'] + '; title: ' + item['title']
        if item['meta'] != None:
            s = s + '; place: ' + item.get('meta').get('venue_name', 'None') + '; date: ' + item.get('meta').get('event_start_date', 'None')
        print(s.encode('utf-8'))

def execute3():
    events = getEventsFromFacebook()
    if events == None:
        return

    dict1 = events.json()['data']
    for item in dict1:
        print('Event processed; id: ' + item['id'] + '; name: ' + item['name'] + '; place: ' + item['place']['name'] + '; time: ' + item['start_time'])

    newEvents = reversed(createNewEvents(dict1))

    writeEventsToFile(str(newEvents), 'fb_events.txt')
    print(str(len(dict1)) + ' events counted')

    for e in newEvents:
        postEvent(e)

    print('Importing facebook events done')

def execute4():
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
    events = getEventsFromFacebook()
    if events == None:
        print('Synchronisation failed, returning')
        return

    dict2 = events.json()['data']
    for item in dict2:
        print('Event found; id: ' + item['id'] + '; name: ' + item['name'] + '; time: ' + item['start_time'])
        if item.get('place') != None and item['place'].get('name') != None:
            print('--place: ' + item['place']['name'] )

     # newEvents = reversed(createNewEvents(dict2))

    # writeEventsToFile(str(newEvents), 'fb_events.txt')
    # print(str(len(dict2)) + ' events counted')

    compare(dict2)

    print('Importing facebook events done')

execute4()
