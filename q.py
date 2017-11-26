import os
import time

def a():
    size = 1000000
    print('Size is ' + str(size) + 'bytes')
    iteration = 0
    chunk_size = 2048
    start = time.time()
    speed = 0
    q = []
    while 1:
        q.append(100)
        if len(q) > size:
            break
        iteration = len(q)
        time.sleep(0.1)
        if time.time() - start > 1:
            delta = time.time() - start
            speed = chunk_size // delta
            start = time.time()
            print(speed)
        # print_progress_bar(iteration, size, speed=speed)


def print_progress_bar(iteration, total, speed=None, prefix='', suffix='', decimals=1, length=100, fill='█'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r{} |{}| {}% {} {} b/s'.format(prefix, bar, percent, suffix, speed), end='\r')
    if iteration == total:
        print()

a()
