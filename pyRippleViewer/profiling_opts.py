
import logging
runProfiler = False
LOGGING = True

logFormatDict = dict(
    format='L{levelno}: {asctime}{msecs: >5.1f}: {name: >30} thr. {thread: >12X}: thr. n. {threadName}: {message}',
    style='{', datefmt='%M:%S:',
    level=logging.INFO)