import requests
from datetime import datetime, timezone
import pytz
import re

import config

fb_base_url = "https://graph.facebook.com"
fb_page_id = "111101134055001"
#page_id = "115563666940099"
fb_fields = "id, name, category, attending_count, description,  end_time, event_times, place,start_time, cover"

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

    if event.get('event_times') != None:
        for subEvent in event['event_times']:
            startTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
            endTime = datetime.strptime(subEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")

            newSubEvent = newEvent.copy()
            newSubEvent['facebook_id'] = subEvent['id']
            newSubEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
            newSubEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
            newEvents.append(newSubEvent)
    else:
        startTime = datetime.strptime(event['start_time'], "%Y-%m-%dT%H:%M:%S%z")
        endTime = datetime.strptime(event['end_time'], "%Y-%m-%dT%H:%M:%S%z")
        newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
        newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
        newEvents.append(newEvent)

    category = 'anders'
    if event.get('name') != None:
        name = event['name'].lower()
        if (('action' in name and not 'actiontraining' in name and not 'action training' in name) or
            ('actie' in name and not 'actietraining' in name and not 'actie training' in name) or
            'luchtalarm' in name):
            category = 'actie'
        elif 'training' in name or 'nvda' in name:
            category = 'training'
        elif ('talk' in name or
                'lezing' in name or
                'introduction' in name or
                'introductie' in name or
                'heading for extinction' in name or
                'what to do about it' in name or
                'what can we do about it' in name or
                'what we can do about it' in name or
                re.search('wat (wij|we) er *aan kunnen doen', name) or
                re.search('wat kunnen (wij|we) er *aan doen', name)):
            category = 'lezing'
        elif 'meeting' in name or 'bijeenkomst' in name:
            category = 'meeting'

    newEvent['category'] = category

    if event.get('place') and event['place'].get('name'):
        location = event['place']['name']
        split = location.split(',')
        if len(split) == 4:
            newEvent['venue_name'] = split[0].strip()
            newEvent['venue_address'] = split[1].strip()

            zipAndCity = split(2).strip()
            split2 = zipAndCity.split(' ')
            if len(split2) == 3:
                zipCode = split2[0] + split2[1]
                newEvent['venue_zipcode'] = zipCode.strip()
                newEvent['venue_city'] = split2[2].strip()
            elif len(split2) == 2:
                newEvent['venue_zipcode'] = split2[0].strip()
                newEvent['venue_city'] = split2[1].strip()

            newEvent['venue_country'] = split(3).strip()
        elif len(split) == 3:
            if split[2].strip() == 'Nederland':
                newEvent['venue_address'] = split[0].strip()

                zipAndCity = split[1].strip()
                split2 = zipAndCity.split(' ')
                if len(split2) == 3:
                    zipCode = split2[0] + split2[1]
                    newEvent['venue_zipcode'] = zipCode.strip()
                    newEvent['venue_city'] = split2[2].strip()
                elif len(split2) == 2:
                    newEvent['venue_zipcode'] = split2[0].strip()
                    newEvent['venue_city'] = split2[1].strip()

                newEvent['venue_country'] = split[2].strip()
            else:
                newEvent['venue_name'] = split[0].strip()
                newEvent['venue_address'] = split[1].strip()

                zipAndCity = split[2].strip()
                split2 = zipAndCity.split(' ')
                if len(split2) == 3:
                    zipCode = split2[0] + split2[1]
                    newEvent['venue_zipcode'] = zipCode.strip()
                    newEvent['venue_city'] = split2[2].strip()
                elif len(split2) == 2:
                    newEvent['venue_zipcode'] = split2[0].strip()
                    newEvent['venue_city'] = split2[1].strip()
        elif len(split) == 2:
            newEvent['venue_address'] = split[1].strip()
            newEvent['venue_city'] = split2[1].strip()
        elif len(split) == 1:
            newEvent['venue_name'] = split[0].strip()
    elif event.get('place') and event['place'].get('location'):
        location = event['place']['location']
        event['venue_lat'] = location.get('latitude')
        event['venue_lon'] = location.get('longitude')

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

def compare(fbEvents):
    for fbEvent in fbEvents:
        wpEvent = wpEventsByFacebookId.get(fbEvent['id'])
        if wpEvent != None:
            print("Match found for facebook_id " + fbEvent['id'])
            # compare and update if necessary
            newEvent = {'id': wpEvent['id']}
            modified = False
            # Unfortunately I have to strip the timezone part because the Meetup events in Wordpress use UTC times as if they were local times.
            startTime = datetime.strptime(fbEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
            start_timestamp = (startTime + startTime.utcoffset()).timestamp()
            endTime = datetime.strptime(fbEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")
            end_timestamp = (endTime + endTime.utcoffset()).timestamp()
            if wpEvent['title'] != fbEvent['name']:
                newEvent['title'] = fbEvent['name']
                modified = True
                print('UPDATED: ""'+ wpEvent['title'] + ' - ' + fbEvent['name'] + '"')
            if wpEvent['content'] != fbEvent['description']:
                newEvent['content'] = fbEvent['description']
                modified = True
                print('UPDATED: ""' + wpEvent['content'] + ' - ' + fbEvent['description'] + '"')

            if wpEvent.get('meta') != None:
                if wpEvent['meta']['event_start_date'] != startTime.strftime('%Y-%m-%d') or wpEvent['meta']['event_start_hour'] != startTime.strftime('%I') or wpEvent['meta']['event_start_minute'] != startTime.strftime('%M') or wpEvent['meta']['event_start_meridian'] != startTime.strftime('%p').lower() or wpEvent['meta']['start_ts'] != str(int(start_timestamp)):
                    newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                    modified = True
                    print('UPDATED: ""' + wpEvent['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
                    print(startTime.strftime('%Y-%m-%d'))
                    print(startTime.strftime('%I'))
                    print(startTime.strftime('%M'))
                    print(startTime.strftime('%p').lower())
                    print(str(int(start_timestamp)))
                if wpEvent['meta']['event_end_date'] != endTime.strftime('%Y-%m-%d') or wpEvent['meta']['event_end_hour'] != endTime.strftime('%I') or wpEvent['meta']['event_end_minute'] != endTime.strftime('%M')or wpEvent['meta']['event_end_meridian'] != endTime.strftime('%p').lower() or wpEvent['meta']['end_ts'] != str(int(end_timestamp)):
                    newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                    modified = True
                    print('UPDATED: ""' + wpEvent['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
                    print(endTime.strftime('%Y-%m-%d'))
                    print(endTime.strftime('%I'))
                    print(endTime.strftime('%M'))
                    print(endTime.strftime('%p').lower())
                    print(str(int(end_timestamp)))
                if wpEvent['meta'].get('_thumbnail_id') == None:
                    # for now add picture when there is none. We may need a way to detect if a picture has been changed
                    if fbEvent.get('cover') != None:
                        newEvent['picture_url'] = fbEvent['cover']['source']
                        modified2 = True

            #TODO: compare all fields and check if event is now a recurring event
            if modified:
                putEvent(newEvent)
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

                        startTime = datetime.strptime(subEvent['start_time'], "%Y-%m-%dT%H:%M:%S%z")
                        start_timestamp = (startTime + startTime.utcoffset()).timestamp()
                        endTime = datetime.strptime(subEvent['end_time'], "%Y-%m-%dT%H:%M:%S%z")
                        end_timestamp = (endTime + endTime.utcoffset()).timestamp()
                        if wpEvent2['title'] != fbEvent['name']:
                            newEvent['title'] = fbEvent['name']
                            modified2 = True
                            print('UPDATED: ""'+ wpEvent2['title'] + ' - ' + fbEvent['name'] + '"')
                        if wpEvent2['content'] != fbEvent['description']:
                            newEvent['content'] = fbEvent['description']
                            modified2 = True
                            print('UPDATED: ""' + wpEvent2['content'] + ' - ' + fbEvent['description'] + '"')
                        if wpEvent2.get('meta') != None:
                            if wpEvent2['meta']['event_start_date'] != startTime.strftime('%Y-%m-%d') or wpEvent2['meta']['event_start_hour'] != startTime.strftime('%I') or wpEvent2['meta']['event_start_minute'] != startTime.strftime('%M')or wpEvent2['meta']['event_start_meridian'] != startTime.strftime('%p').lower() or wpEvent2['meta']['start_ts'] != str(int(start_timestamp)):
                                newEvent['start_date'] = startTime.strftime("%Y-%m-%d %H:%M")
                                modifie2d = True
                                print('UPDATED: ""' + wpEvent2['meta']['event_start_date'] + ' - ' + str(startTime) + '"')
                                print(str(int(start_timestamp)))
                            if wpEvent2['meta']['event_end_date'] != endTime.strftime('%Y-%m-%d') or wpEvent2['meta']['event_end_hour'] != endTime.strftime('%I') or wpEvent2['meta']['event_end_minute'] != endTime.strftime('%M')or wpEvent2['meta']['event_end_meridian'] != endTime.strftime('%p').lower() or wpEvent2['meta']['end_ts'] != str(int(end_timestamp)):
                                newEvent['end_date'] = endTime.strftime("%Y-%m-%d %H:%M")
                                modified2 = True
                                print('UPDATED: ""' + wpEvent2['meta']['event_end_date'] + ' - ' + str(endTime) + '"')
                                print(str(int(start_timestamp)))
                            if wpEvent2['meta'].get('_thumbnail_id') == None:
                                # for now add picture when there is none. We may need a way to detect if a picture has been changed
                                if fbEvent.get('cover') != None:
                                    newEvent['picture_url'] = fbEvent['cover']['source']
                                    modified2 = True


                        #TODO: compare all fields and check if event is now a recurring event
                        if modified2:
                            putEvent(newEvent)
                        else:
                            print("No updates detected")
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

                        # TODO: a date is added to a set of recurring events. We could add it, but then, what would we do when such a date is removed?

                # find a way to match events with eachother
                #if wpEvent.content.startsWith('<input type="hidden" id="facebook_id" name="facebook_id" value="'):
                #     pos1 = 65
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
        print('Event found; id: ' + item['id'] + '; name: ' + item['name'] + '; place: ' + item['place']['name'] + '; time: ' + item['start_time'])

     # newEvents = reversed(createNewEvents(dict2))

    # writeEventsToFile(str(newEvents), 'fb_events.txt')
    # print(str(len(dict2)) + ' events counted')

    compare(dict2)

    print('Importing facebook events done')

execute4()
