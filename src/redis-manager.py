from kazoo.client import KazooClient
from kazoo.client import KazooState
import time
import threading
import settings
import os
import datetime
import threading
import json
import logging
import logging.config
import sys
import getopt

class RedisZkRegister(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port
        self.lastAlive = time.time()
        self.client = None
        self.expired = threading.Event()
        self.logger=logging.getLogger('redis')
        
    def run(self):
        while(True):
            try:
                if self.checkalive():
                    if(self.client == None):
                        self.connect()
                        
                    elif (self.expired.is_set()):
                        self.reconnect()
                        self.expired.clear()
                    
                    self.lastAlive = time.time()
                else:
                    if(time.time() - self.lastAlive > settings.checkTimeoutSec):
                        self.close()
            except Exception, ex:
                self.log(ex)
            finally:
                time.sleep(settings.checkIntervalSec)
            
    def checkalive(self):
        ret = False
        try:
            cmd = settings.redisCli + ' -p %d PING' % self.port
            ret = os.popen(cmd).readline().find("PONG") != -1
        except Exception, e:
            self.log('check alive failed', e)
            
        self.logger.info('[%d] check alive' % self.port + str(ret))
        return ret
           
    def reconnect(self):
        self.log('begin reconnect')
        self.close()
        self.connect()
        self.log('reconnect success')
           
    def connect(self):
        # Once connected, the client will attempt to stay connected regardless of 
        # intermittent connection loss or Zookeeper session expiration.
        #***we need not create new ZookeeperClient When Session Expired like java client
        # but here we recreate new KazooClient when Session Expired
        def conn_listener(state):
            try:
                self.log('connected changed:', state)
                if state == KazooState.LOST:  # Session Expired
                    self.expired.set()
                    self.log('session Expired')
                elif state == KazooState.SUSPENDED:  # disconnected from Zookeeper
                    pass
                else:  # KazooState.CONNECTED ,connected/reconnected to Zookeeper
                    pass
            except Exception, e:
                self.log(e)
        
        self.client = KazooClient(hosts=settings.zkServers, timeout=settings.zkTimeoutSec)
        self.log('begin connect to', settings.zkServers, 'timeout:', settings.zkTimeoutSec, "s")
        self.client.add_listener(conn_listener)
        self.client.start()
        self.log('connect to', settings.zkServers, 'success')
        self.create_node()
 
    def create_node(self):
        self.log('ensure path', settings.zkRootPath)     
        self.client.ensure_path(settings.zkRootPath)
        self.log('begin create node');
        data=self.create_nodeValue()
        self.log('RouteValue:',data)
        self.client.create(settings.zkRootPath + '/' + settings.RoleName, value=data, ephemeral=True, sequence=True)
        self.log('create node success')
        
    def create_nodeValue(self):
        node = {}
        node['RoleName'] = settings.RoleName
        node['Policy'] = settings.Policy
        node['SiteName'] = settings.SiteName
        node['Weight'] = settings.Weight
        node['RouteId'] = 0
        node['NodeOrder']=0
        node['Enabled'] = 1
        node['RouteValue'] = settings.RouteValue % (settings.localIp, self.port)
        
        return json.dumps(node)
                  
    def close(self):
        client = self.client
        self.client = None
        
        if(client != None):
            self.log('begin close node')
            client.stop()
            client.close()
            self.log('close node success')
    
    def log(self, *msg):
            log= '[%d]' % self.port, ' '.join([str(d) for d in msg])
            self.logger.warn(log)

def daemonize():  
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError,e:
            sys.stderr.write("Fork 1 has failed --> %d--[%s]\n" \
                             % (e.errno,e.strerror))
            sys.exit(1)
 
        os.chdir('/')
        #detach from terminal
        os.setsid()
        #file to be created
        os.umask(0)
 
        try:
            pid = os.fork()
            if pid > 0:
                print "Daemon process pid %d" % pid
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("Fork 2 has failed --> %d--[%s]" \
                             % (e.errno, e.strerror))
            sys.exit(1)
 
        sys.stdout.flush()
        sys.stderr.flush()
        if sys.platform != 'darwin': # This block breaks on OS X
            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            si = file( os.devnull, 'r')
            so = file( os.devnull, 'a+')
            se = file( os.devnull, 'a+', 0)
            
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())

def exists_instance():
    count=(int)(os.popen('ps -ef | grep redis-manager.py| grep -v grep| wc -l').readline())
    return count>1 # current + exists (2)
                     
if __name__ == '__main__':
    curpath=os.path.split( os.path.realpath( sys.argv[0] ) )[0]
    logging.config.fileConfig(curpath+'/logging.conf')
    
    options,args = getopt.getopt(sys.argv[1:],"ds:",['daemon','singleton'])
    
    isMulti=False
    for name,value in options:
        if name in('-s','--singleton') and value=='False':
            isMulti=True
        
    if(not isMulti and exists_instance()):
        raise Exception("redis-manager instance already exits!!,or use -s False to allow multi-instance!")
    
    for name,value in options:
        if name in ('-d','--daemon'):
            daemonize()
            
    registers = []
    for port in settings.ports:
        reg = RedisZkRegister(port)
        registers.append(reg)
        reg.setDaemon(True)
        reg.start()
        
    while(True):
        time.sleep(10)
