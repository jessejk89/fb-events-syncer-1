from hashlib import blake2b

def bhash(content):
    if content == None:
        return None
    return blake2b(bytes(content, 'utf-8')).hexdigest()
