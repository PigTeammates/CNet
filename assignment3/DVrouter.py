####################################################
# DVrouter.py
# Name: Yuxuan Lao, Junbin Huang
# JHED ID: ylao2, jhuan129
#####################################################

import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
from copy import deepcopy


class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0

        self.dis_cost = {}      # used to record distance, ip: dis
        self.out_ports = {}     # used to record next port, ip: port
        self.forward_table = {} # destination ip: port
        self.DV = {}            # destination ip: (distance, next hop)
        self.neighborDV = {}    # neighbor ip: DV

        # Hints: initialize local state
        self.DV[self.addr] = (0, None)
        # The distance vector stores dst ip -> (distance, next hop).
        

    def _update_DV(self, dst):
        if self.DV[dst][1] is not None:
            if self.DV[dst][1] not in self.dis_cost:
                self.DV[dst] = (16, None)
                self.forward_table.pop(dst)
            elif  self.DV[dst][1] not in self.neighborDV or dst not in self.neighborDV[self.DV[dst][1]]:
                self.DV[dst] = (self.dis_cost[self.DV[dst][1]], self.DV[dst][1])
                self.forward_table[dst] = self.out_ports[self.DV[dst][1]]
            else:
                newD = self.dis_cost[self.DV[dst][1]] + self.neighborDV[self.DV[dst][1]][dst][0]
                self.DV[dst] = (newD, self.DV[dst][1])
                self.forward_table[dst] = self.out_ports[self.DV[dst][1]]


    def _update_neighbors(self, dst):
        for neighbor in self.neighborDV:
            if dst in self.neighborDV[neighbor]:
                new_dst = self.dis_cost[neighbor] + self.neighborDV[neighbor][dst][0]
                if self.DV[dst][0] > new_dst:
                    self.DV[dst] = (new_dst, neighbor)
                    self.forward_table[dst] = self.out_ports[neighbor]


    def update(self):
        for dst in self.dis_cost:
            if dst not in self.DV:
                self.DV[dst] = (self.dis_cost[dst], dst)
                self.forward_table[dst] = self.out_ports[dst]

        for dst in self.DV:
            if dst == self.addr:
                continue
            self._update_DV(dst)
            self._update_neighbors(dst)
                      

    def broadcast(self):
        m = {}
        for neighbor in self.out_ports:
            m["DV"] = deepcopy(self.DV)
            for dst in m["DV"]:
                if dst != neighbor and m["DV"][dst][1] == neighbor:
                    m["DV"][dst] = (16, None)
            self.send(self.out_ports[neighbor], \
                Packet(Packet.ROUTING, self.addr, None, content=dumps(m)))


    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():

            if packet.dstAddr and packet.dstAddr in self.forward_table:
                nPort = self.forward_table[packet.dstAddr]
                self.send(nPort, packet)
        else:
            newDV = loads(str(packet.content))["DV"]
            srcAddr = packet.srcAddr

            if srcAddr not in self.neighborDV or cmp(newDV, self.neighborDV[srcAddr]):
                self.neighborDV[srcAddr] = newDV
                for dst in newDV:
                    if dst not in self.DV:
                        self.DV[dst] = (16, None)

                self.update()
                self.broadcast()


    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors
        self.dis_cost[endpoint] = cost
        self.out_ports[endpoint] = port
        self.update()
        self.broadcast()


    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors
        keys, vals = zip(*self.out_ports.items())
        addr = keys[vals.index(port)]

        self.out_ports.pop(addr)
        self.dis_cost.pop(addr)
        self.neighborDV.pop(addr)
        for dst in keys:
            if self.forward_table[dst] == port:
                self.forward_table.pop(dst)
                self.DV[dst] = (16, None)
        self.update()
        self.broadcast()

    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # broadcast the distance vector of this router to neighbors
            self.broadcast()


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return repr(self.DV)
    
