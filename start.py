import schedule
import time
import config
import sys
import traceback

import sync

dryRun = False
fbToFile = False
outputFile = None
fbFromFile = False
inputFile = None

def synchronizeWithFile():
    original_stdout = sys.stdout # Save a reference to the original standard output
    #original_stderr = sys.stderr # Save a reference to the original standard error
    f = open(config.logFile, 'a')
    try:
        sys.stdout = f # Change the standard output to the file we created.
        #sys.stderr = f
        sync.synchronize(dryRun, fbToFile, outputFile, fbFromFile, inputFile)
    except:
        print("An error occured while running the synchronization script, trying again next time")
        traceback.print_exc(file=f)
    finally:
        sys.stdout = original_stdout # Reset the standard output to its original value
        #sys.stderr = original_stderr # Reset the standard output to its original value
        f.close()

if __name__ == "__main__":
    i = 1
    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            print("Executing dry run. Results are not posted to wordpress API.")
            dryRun = True
        elif arg == "--fb-to-file":
            print("Writing facebook events to a specified file " + sys.argv[i+1] + ".")
            fbToFile = True
            outputFile = sys.argv[i+1]
        elif arg == "--fb-from-file":
            print("Getting facebook events from a specified file " + sys.argv[i+1] + ".")
            fbFromFile = True
            inputFile = sys.argv[i+1]
        i = i + 1

schedule.every(config.intervalHours).hours.do(synchronizeWithFile)

synchronizeWithFile()

while True:
    schedule.run_pending()
    time.sleep(1)
