#!/usr/bin/env python

# Copyright (C) Michael Adam <obnox@samba.org> 2011,2015
#
# License GPLv3+
#
# TODO:
#  * check success of fcntl calls
#  * implement mmap?
#  * catch Ctrl-C nicely

import fcntl
import struct
import os
from optparse import OptionParser
import time
import sys

def reset_time():
    #return time.clock()
    return time.time()

def time_elapsed_since(since):
    #time2 = time.clock()
    time2 = time.time()
    return time2 - since

def fcntl_range(fd, lock_type, offset, length):
    lockdata = struct.pack('hhllhh', lock_type, 0, offset, length, 0, 0)
    return fcntl.fcntl(fd, fcntl.F_SETLKW, lockdata)

def lock_range(fd, offset, length):
    return fcntl_range(fd, fcntl.F_WRLCK, offset, length)

def unlock_range(fd, offset, length):
    return fcntl_range(fd, fcntl.F_UNLCK, offset, length)

def lock_byte(fd, offset):
     return lock_range(fd, offset, 1)

def unlock_byte(fd, offset):
     return unlock_range(fd, offset, 1)


def ping_pong(fd, num_locks, do_reads, do_writes, do_mmap):
    ret = os.ftruncate(fd, num_locks + 1)
    if (ret == -1):
        print "ERROR: truncating failed"
        return

    lap_start = reset_time()
    lock_byte(fd, 0)
    # if passed a packed struct, fcntl returns a packed struct, not int...
    #if (lock_byte(fd, 0) != 0):
    #    print "ERROR: lock at 0 failed!"
    #    return

    offset = 0
    count = 0
    loops = 0
    val = [ 0 for x in range(num_locks) ]
    #print val
    incr = 0
    last_incr = 0

    while True:
        new_offset = (offset + 1) % num_locks

        #lock_byte(fd, new_offset)
        lock_range(fd, new_offset, 1)

        if do_reads:
            os.lseek(fd, offset, os.SEEK_SET)
            c = os.read(fd, 1)
            if (len(c) != 1):
                print "ERROR: reading one byte"
                exit(1)
            bb = struct.unpack('B', c)
            if len(bb) != 1:
                print "ERROR: illegal number (%d) of bytes read" % len(bb)
                exit(1)
            n = bb[0]
            incr = ( 256 + n - val[offset] ) % 256
            val[offset] = n

        if do_writes:
            n = (val[offset] + 1) % 256
            c = struct.pack('B', n)
            os.lseek(fd, offset, os.SEEK_SET)
            os.write(fd, c)

        #unlock_byte(fd, offset)
        unlock_range(fd, offset, 1)

        offset = new_offset
        count = count + 1

        if (loops > num_locks) and (incr != last_incr):
            last_incr = incr
            msg = "data increment = %d\n" % incr
            sys.stdout.write(msg)
            sys.stdout.flush()

        if time_elapsed_since(lap_start) > 1.0:
            msg = "%8d locks/sec\r" % (2*count/time_elapsed_since(lap_start))
            sys.stdout.write(msg)
            sys.stdout.flush()
            lap_start = reset_time()
            count = 0

        loops = loops + 1



def main():
    parser = OptionParser()

    parser.add_option("-r", "--read", help="do reads", default=False, action="store_true")
    parser.add_option("-w", "--write", help="do writes", default=False, action="store_true")
    # TODO:parser.add_option("-m", "--mmap", help="use mmap", default=False, action="store_true")

    (options, args) = parser.parse_args()

    if (len(args) != 2):
        print "ERROR: two arguments required"
        return 1

    file_name = args[0]

    num_locks = int(args[1])

    fd = os.open(file_name, os.O_RDWR|os.O_CREAT, 0600)
    if (fd == -1):
        print "ERROR: opening file failed"
        return 1

    ping_pong(fd, num_locks, options.read, options.write, options.mmap)

    os.close(fd)

    return 0

main()

# vim: set ts=4 et sw=4:
