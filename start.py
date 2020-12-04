import schedule
import time

import sync

schedule.every(5).minutes.do(sync.synchronizeWithFile)

while True:
    try:
        schedule.run_pending()
    except:
        print("An error occured while running the synchronization script")
    time.sleep(1)
