###############################################################################
# receiver.py
# Name:
# JHED ID:
###############################################################################

import sys
import socket

from util import *

PACKET_SIZE = 1472  # 1500(MF)-8(UDP_H)-20(IP_H) = 1472 bytes


def send_signal(s, seq_no, typ, recv_ip, recv_port):
    pkt_header = PacketHeader(type=typ, seq_num=seq_no, length=0)
    pkt_header.checksum = compute_checksum(pkt_header / "")
    pkt = pkt_header / ""
    s.sendto(str(pkt), (recv_ip, recv_port))


def verify_packet(pkt_header, msg):
    pkt_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    computed_checksum = compute_checksum(pkt_header / msg)
    return True if pkt_checksum == computed_checksum else False


def recv_signal(s):
    # receive packet
    pkt, address = s.recvfrom(PACKET_SIZE)

    # extract header and payload
    pkt_header = PacketHeader(pkt[:16])
    msg = pkt[16:16 + pkt_header.length]

    # verify checksum
    if not verify_packet(pkt_header, msg):
        return None, None

    return pkt_header, address


def recv_data(s, sender_ip, sender_port):
    # receive packet
    pkt, address = s.recvfrom(PACKET_SIZE)

    if address[0] != sender_ip or address[1] != sender_port:
        return None, None
    # extract header and payload
    pkt_header = PacketHeader(pkt[:16])
    msg = pkt[16:16 + pkt_header.length]

    # verify checksum
    if not verify_packet(pkt_header, msg):
        return None, None

    return pkt_header, msg


def receiver(receiver_port, window_size):
    """ TODO: Listen on socket and print received message to sys.stdout """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('127.0.0.1', receiver_port))

    while True:
        window = dict()     # window to store seq_no-data chunk
        next_seq = 0        # next sequence number to be ACK

        # try to receive packet with START
        while True:
            pkt_header, sender_addr = recv_signal(s)
            if pkt_header and pkt_header.type == START:
                addr = sender_addr
                send_signal(s, pkt_header.seq_num, ACK, *addr)
                break

        while True:
            pkt_header, msg = recv_data(s, *addr)

            # drop packet with corruption or wrong addr
            if not pkt_header:
                continue

            # drop packet with START in the mid of conn
            if pkt_header.type == START and next_seq == 0:
                send_signal(s, pkt_header.seq_num, ACK, *addr)

            if pkt_header.type == DATA:
                seq_no = pkt_header.seq_num

                # drop all packets greater than the window
                if seq_no >= next_seq + window_size:
                    continue

                # buffer out-of-order packets
                if seq_no != next_seq:
                    if seq_no > next_seq:
                        window[seq_no] = msg    # buffers out-of-order packets
                    send_signal(s, pkt_header.seq_num, ACK, *addr)
                else:
                    window[seq_no] = msg
                    while next_seq in window:
                        sys.stdout.write(window[next_seq])
                        sys.stdout.flush()
                        next_seq += 1
                    send_signal(s, next_seq, ACK, *addr)

            if pkt_header.type == END:
                send_signal(s, next_seq, ACK, *addr)
                break


def main():
    """ Parse command-line argument and call receiver function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python receiver.py [Receiver Port] [Window Size]")
    receiver_port = int(sys.argv[1])
    window_size = int(sys.argv[2])
    receiver(receiver_port, window_size)


if __name__ == "__main__":
    main()
