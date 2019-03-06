###############################################################################
# sender.py
# Name: Yuxuan Lao, Junbin Huang
# JHED ID: ylao2, jhuan129
###############################################################################

import sys
import socket
import time
import random

from util import *

PACKET_SIZE = 1472      # 1500(MF)-8(UDP_H)-20(IP_H) = 1472 bytes
PAYLOAD_SIZE = 1456     # 1472(PACKET_SIZE)-4*4(Header) = 1456 bytes
ret_time = 0.5          # retransmission time


def send_signal(s, seq_no, typ, recv_ip, recv_port):
    pkt_header = PacketHeader(type=typ, seq_num=seq_no, length=0)
    pkt_header.checksum = compute_checksum(pkt_header / "")
    pkt = pkt_header / ""
    s.sendto(str(pkt), (recv_ip, recv_port))


def send_data(s, window, seq, recv_ip, recv_port):
    for seq_no in seq:
        msg = window[seq_no][1]
        pkt_header = PacketHeader(type=DATA, seq_num=seq_no, length=len(msg))
        pkt_header.checksum = compute_checksum(pkt_header / msg)
        pkt = pkt_header / msg
        s.sendto(str(pkt), (recv_ip, recv_port))


def verify_packet(pkt_header, msg):
    pkt_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    computed_checksum = compute_checksum(pkt_header / msg)
    return True if pkt_checksum == computed_checksum else False


def recv_signal(s, receiver_ip, receiver_port):
    # try to receive a packet
    try:
        pkt, address = s.recvfrom(PACKET_SIZE)
    except socket.error:
        return None

    if address[0] != receiver_ip or address[1] != receiver_port:
        return None
    # extract header and payload
    pkt_header = PacketHeader(pkt[:16])
    msg = pkt[16:16 + pkt_header.length]

    # verify checksum
    if not verify_packet(pkt_header, msg):
        return None

    return pkt_header


def sender(receiver_ip, receiver_port, window_size):
    """ TODO: Open socket and send message from sys.stdin """
    window = dict()     # window to store seq_no-(timer, data chunk)
    next_seq = 0        # next sequence number to be ACK
    seq_data = 0        # latest sequence number of data chunk
    eof = False         # reach the end of stdin

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # start with a START along with a random seq_no
    rand_seq = random.randrange(0, 2**32-1)
    s.settimeout(ret_time)
    while True:
        send_signal(s, rand_seq, START, receiver_ip, receiver_port)
        # sender blocked on waiting ACK
        pkt_header = recv_signal(s, receiver_ip, receiver_port)
        if pkt_header and pkt_header.type == ACK and pkt_header.seq_num == rand_seq:
            break

    s.setblocking(False)  # set non-blocking mode of the socket

    # read data from stdin and send to receiver
    while not eof or len(window) > 0:
        pkt_header = recv_signal(s, receiver_ip, receiver_port)
        new_msg = list()    # a list storing the seq_no of the refilled msg

        if pkt_header and pkt_header.type == ACK:
            ack_seq = pkt_header.seq_num
            # try to clear the buffer
            if ack_seq in window:
                window.pop(ack_seq)

            # retransmit any packet with timeout
            timeout_msg = list()    # a list storing the seq_no of the timeout msg
            for seq_no, val in window.items():
                timer = val[0]
                if time.time() - timer > ret_time:
                    timeout_msg.append(seq_no)
                    val[0] = time.time()    # reset the timer

            if len(timeout_msg) > 0:
                send_data(s, window, timeout_msg, receiver_ip, receiver_port)

            # try to advance the window
            next_seq = sorted(window.keys())[0] if len(window) > 0 else seq_data

        # refill the window with data, if any
        while not eof and seq_data + 1 < next_seq + window_size:
            msg = sys.stdin.read(PAYLOAD_SIZE)
            if not msg:
                eof = True
                break
            window[seq_data] = [time.time(), msg]
            new_msg.append(seq_data)
            seq_data += 1

        # transmit new packets, if any
        if len(new_msg) > 0:
            send_data(s, window, new_msg, receiver_ip, receiver_port)

    s.setblocking(True)  # reset blocking mode of the socket

    # send an END to mark the end of connection
    s.settimeout(ret_time)
    while True:
        send_signal(s, next_seq, END, receiver_ip, receiver_port)
        # sender blocked on waiting ACK
        pkt_header = recv_signal(s, receiver_ip, receiver_port)
        # print pkt_header.type, pkt_header.seq_num
        if pkt_header and pkt_header.type == ACK and pkt_header.seq_num == next_seq:
            break

    s.close()


def main():
    """ Parse command-line arguments and call sender function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Receiver IP] [Receiver Port] [Window Size] < [message]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    sender(receiver_ip, receiver_port, window_size)


if __name__ == "__main__":
    main()
