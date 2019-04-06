####################################################
# LSrouter.py
# Name:
# JHED ID:
#####################################################

import sys
import networkx as netx
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads


class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state
        self.forwarding_table = dict()
        self.ports = dict()
        self.link_states = defaultdict(list)
        self.seq_ns = defaultdict(lambda: 0)
        self.incr_num = 0

    def update(self):
        # construct the network graph with link states
        graph = netx.Graph()
        for links in self.link_states.values():
            graph.add_weighted_edges_from(links)

        # update forwarding table
        for addr in graph.nodes():
            if addr != self.addr:
                try:
                    path = netx.dijkstra_path(graph, source=self.addr, target=addr)
                    # next router on the way to dstAddr
                    next_addr = path[1]
                    # link states message may have been outdated
                    if next_addr not in self.ports:
                        continue
                    self.forwarding_table[addr] = self.ports[next_addr]
                except netx.NetworkXNoPath:
                    pass

    def broadcast(self):
        my_links = self.link_states[self.addr]
        message = (self.incr_num, my_links)
        packet = Packet(Packet.ROUTING, self.addr, None, content=dumps(message))
        for port in self.ports.values():
            self.send(port, packet)
            
        # update the sequence number
        self.incr_num += 1

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            # Hints: this is a normal data packet
            if packet.dstAddr and packet.dstAddr in self.forwarding_table:
                next_port = self.forwarding_table[packet.dstAddr]
                self.send(next_port, packet)
        else:
            # Hints: this is a routing packet generated by your routing protocol
            sqn, links = loads(packet.content)
            addr = packet.srcAddr
            assert links
            assert addr == links[0][0]
            assert addr != self.addr
            last_sqn = self.seq_ns[addr]

            # check the sequence number
            if sqn >= last_sqn and links != self.link_states[addr]:
                # update the local copy of the link state
                self.link_states[addr] = links
                # update the forwarding table
                self.update()
                # broadcast the packet to other neighbors
                for neighbor, nport in self.ports.items():
                    # never broadcast the packet to its source
                    if neighbor != addr and nport != port:
                        self.send(nport, packet)
            
            # update with the latest seq_no
            self.seq_ns[addr] = sqn

    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # update the forwarding table
        my_links = self.link_states[self.addr]
        my_links.append([self.addr, endpoint, cost])
        my_links.sort()
        self.ports[endpoint] = port
        self.update()
        # print "%s_%s_%d" % (self.addr, endpoint, cost)

        # broadcast the new link state of this router to all neighbors
        self.broadcast()

    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # find out the corresponding addr
        keys, vals = zip(*self.ports.items())
        addr = keys[vals.index(port)]
        
        self.ports.pop(addr)
        self.link_states[self.addr] = [x for x in self.link_states[self.addr] if x[1] != addr]
        self.link_states[addr] = [x for x in self.link_states[addr] if x[1] != self.addr]

        # update the forwarding table
        self.update()
        # broadcast the new link state of this router to all neighbors
        self.broadcast()

    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # broadcast the link state of this router to all neighbors
            self.broadcast()

    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return repr(self.forwarding_table)
