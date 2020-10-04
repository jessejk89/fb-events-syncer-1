import re

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
