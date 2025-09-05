from dnslib.server import DNSServer, BaseResolver
from dnslib import RR, QTYPE, A
import time

class FakeResolver(BaseResolver):
    def resolve(self, request, handler):
        #print(request)
        reply = request.reply()
        qname = request.q.qname
        reply.add_answer(RR(qname, QTYPE.A, rdata=A("192.168.3.1"), ttl=60))
        return reply

resolver = FakeResolver()
server = DNSServer(resolver, port=53, address="192.168.3.1")
server.start_thread()

while True:
    time.sleep(1)
