import re
import requests

import utils

regex = r'('

# Scheme (HTTP, HTTPS, FTP and SFTP):
regex += r'(?:(?:(?:(?P<protocol>https?|s?ftp):\/\/)?'

# www:
regex += r'(?:www\.)?)'

#Email prefix
regex += r'|(?P<email_prefix>[a-zA-Z0-9_.+-]+@))'

regex += r'(?:'

# Host and domain (including ccSLD):
regex += r'(?:(?:[A-Z0-9][A-Z0-9-]{0,61}[A-Z0-9]\.)+)'

# TLD:
regex += r'(?:[A-Z]{2,})'

# IP Address:
regex += r'|(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'

regex += r')'

# Port:
regex += r'(?::(?:\d{1,5}))?'

# Query path:
regex += r'(?:(?:\/\S+)*[A-Z0-9/])?'

regex += r')'

def substituteUrl(m):
    result = '<a href="' + m.group(0) + '">' + m.group(0) + '</a>'

    if m.group('email_prefix') != None: # match has an email prefix
        result = '<a href="mailto: ' + m.group(0) + '">' + m.group(0) + '</a>'
    elif m.group('protocol') == None:
        result =  '<a href="http://' + m.group(0) + '">' + m.group(0) + '</a>'

    return result

def parseCategoryInformation(event, newEvent):
    # make an educated guess about the category: review is needed by a human
    category = 'meeting'
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

def parseLocationInformation(event, newEvent):
    # location
    if event.get('place') and event['place'].get('name'):
        place_name = event['place']['name']
        location = event['place'].get('location')

        if location != None: # There is a location instance
            city = location.get('city')
            if city != None:
                newEvent['venue_city'] = city
            country = location.get('country')
            if country != None:
                newEvent['venue_country'] = country
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            if latitude != None and longitude != None:
                newEvent['venue_lat'] = latitude
                newEvent['venue_lon'] = longitude
            street = location.get('street')
            if street != None:
                newEvent['venue_address'] = street
            zip = location.get('zip')
            if zip != None:
                newEvent['venue_zipcode'] = zip

            newEvent['venue_name'] = place_name
        else: # All information needs to be parsed from the name field
            split = place_name.split(',')
            if len(split) == 4:
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

                newEvent['venue_country'] = split[3].strip()
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
                elif len(split2) == 1:
                    newEvent['venue_city'] = split[1].strip()
            elif len(split) == 1:
                newEvent['venue_name'] = split[0].strip()

    # If an event is online venue_name and venue_address must be set to 'Online' for the filter on the website to work
    # Unfortunately, this might cause important values to be overwritten in some cases
    if event.get('is_online') and event['is_online'] == True:
        newEvent['venue_name'] = 'Online'
        newEvent['venue_address'] = 'Online'


def parseOwnerInformation(event, newEvent):

    # owner field contains information about the organizer
    owner = event.get('owner')
    if owner != None:
        name = owner.get('name')
        if name != None:
            newEvent['organizer_name'] = name
        emails = owner.get('emails')
        if emails != None and len(emails) > 0:
            newEvent['organizer_email'] = emails[0]
        phone = owner.get('phone')
        if phone != None:
            newEvent['organizer_phone'] = phone
        website = owner.get('website')
        if website != None:
            newEvent['organizer_url'] = website

        if name == 'Extinction Rebellion NL':
            # overwrites the value set above
            newEvent['organizer_email'] = 'info@extinctionrebellion.nl'


def parseContent(event, newEvent):
    if event.get('description') != None:
        description = event['description']
        description = re.sub('[?&]fbclid=\S*', '', description, flags=re.I)
        #description = re.sub(r'((?:(https?|s?ftp):\/\/)?(?:www\.)?((?:(?:[A-Z0-9][A-Z0-9-]{0,61}[A-Z0-9]\.)+)([A-Z]{2,6})|(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))(?::(\d{1,5}))?(?:(\/\S+)*))', r'<a href="\1">\1</a>', description)
        description = re.sub(regex, substituteUrl, description, flags=re.I)
        newEvent['content'] = description

# Hashes can be used to compare events and find out whether they have changed or not.
# It is important to only compare the original facebook events because wordpress events can be changed manually.
def createFacebookHashValuesRecurringEvent(fbEvent, parentFbEvent, newEvent):
    newEvent['name_hash'] = utils.bhash(parentFbEvent.get('name'))
    newEvent['description_hash'] = utils.bhash(parentFbEvent.get('description'))
    newEvent['start_time_hash'] = utils.bhash(fbEvent.get('start_time'))
    newEvent['end_time_hash'] = utils.bhash(fbEvent.get('end_time'))
    newEvent['place_hash'] = utils.bhash(str(parentFbEvent.get('place')))
    newEvent['owner_hash'] = utils.bhash(str(parentFbEvent.get('owner')))
    #newEvent['cover_hash'] = utils.bhash(str(parentFbEvent.get('cover')))

    # the acual image needs to be hashed because facebook changes the source url at least once a day, which leads to false positives
    if parentFbEvent.get('cover') != None and parentFbEvent['cover'].get('source') != None:
        response = requests.get(parentFbEvent['cover']['source'])
        newEvent['_cover_bytes_hash'] = utils.bhash(str(response.content))

def createFacebookHashValues(fbEvent, newEvent):
    newEvent['name_hash'] = utils.bhash(fbEvent.get('name'))
    newEvent['description_hash'] = utils.bhash(fbEvent.get('description'))
    newEvent['start_time_hash'] = utils.bhash(fbEvent.get('start_time'))
    newEvent['end_time_hash'] = utils.bhash(fbEvent.get('end_time'))
    newEvent['place_hash'] = utils.bhash(str(fbEvent.get('place')))
    newEvent['owner_hash'] = utils.bhash(str(fbEvent.get('owner')))
    #newEvent['cover_hash'] = utils.bhash(str(fbEvent.get('cover')))

    # the acual image needs to be hashed because facebook changes the source url at least once a day, which leads to false positives
    if fbEvent.get('cover') != None and fbEvent['cover'].get('source') != None:
        response = requests.get(fbEvent['cover']['source'])
        newEvent['_cover_bytes_hash'] = utils.bhash(str(response.content))
