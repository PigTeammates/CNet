import sys
import socket
import random
import time
from collections import deque


from util import *

def main():
    """Parse command-line argument and call receiver function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Listening Port] [Destination IP] [Destination Port]")
    listening_port = int(sys.argv[1])
    destination_ip = sys.argv[2]
    destination_port = int(sys.argv[3])

    #Listen
    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.bind(('127.0.0.1', listening_port))
    s1.settimeout(0)

    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.settimeout(0)

    pktQueue = deque()
    timeQueue = deque()

    delayTime = 100
    base_time = time.time()*1000

    sender_info = ()

    while True:
        # receive packet from sender
        try: 
            pkt, address = s1.recvfrom(2048)
            ## extract header and payload
            pkt_header = PacketHeader(pkt[:16])
            msg = pkt[16:16+pkt_header.length]

            if pkt_header.type == 0:
                sender_info = address
            
            if cmp(address, sender_info)==0:

                rand = random.randint(0,20)
                # rand = 100
                if(rand == 0):
                    # corruption
                    pkt_header.checksum = random.randint(0,999)
                    pkt = pkt_header / msg
                    s2.sendto(str(pkt), (destination_ip, destination_port))
                    #print("Packet %s corrupted" %(pkt_header.seq_num))
                elif(rand == 1):
                    # delay
                    pktQueue.append(pkt)
                    cur_time = time.time()*1000 - base_time
                    timeQueue.append(cur_time + delayTime)
                elif(rand == 2):
                    # drop
                    #print("Packet %s dropped" %(pkt_header.seq_num))
                    pass
                else:
                    # normal
                    s2.sendto(pkt, (destination_ip, destination_port))
                    # print("Packet %s send to receiver" %(pkt_header.seq_num))
                
                cur_time = time.time()*1000 - base_time
                while len(timeQueue)!=0 and timeQueue[0]>= cur_time :
                    pkt = pktQueue[0]
                    pktQueue.popleft()
                    timeQueue.popleft()
                    s2.sendto(pkt, (destination_ip, destination_port))

                    pkt_header = PacketHeader(pkt[:16])
                    #print("Packet %s delay send to receiver" %(pkt_header.seq_num))

            else:
                pass
                '''
                #print "send to receiver\n"
                s2.sendto(pkt, sender_info)
                #print("Packet %s send to sender" %(pkt_header.seq_num))
                '''

        except:
            pass
            ##print "listen to sender timeout"

        try:
            pkt, address = s2.recvfrom(2048)
            ## extract header and payload
            pkt_header = PacketHeader(pkt[:16])
            msg = pkt[16:16+pkt_header.length]

            print pkt_header.type, pkt_header.seq_num
            s1.sendto(pkt, sender_info)
            # print("Packet %s send to sender" %(pkt_header.seq_num))
        except:
            pass
            ##print "listen to sender timeout"




if __name__ == "__main__":
    main()
