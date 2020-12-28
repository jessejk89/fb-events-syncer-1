import schedule
import time
import config
import sys
import traceback

import sync

def synchronizeWithFile():
    original_stdout = sys.stdout # Save a reference to the original standard output
    #original_stderr = sys.stderr # Save a reference to the original standard error
    f = open(config.logFile, 'a')
    try:
        sys.stdout = f # Change the standard output to the file we created.
        #sys.stderr = f
        sync.synchronize()
    except:
        print("An error occured while running the synchronization script, trying again next time")
        traceback.print_exc(file=f)
    finally:
        sys.stdout = original_stdout # Reset the standard output to its original value
        #sys.stderr = original_stderr # Reset the standard output to its original value
        f.close()

schedule.every(config.intervalHours).hours.do(synchronizeWithFile)
#schedule.every(config.intervalHours).minutes.do(synchronizeWithFile)

while True:
    schedule.run_pending()
    time.sleep(1)
