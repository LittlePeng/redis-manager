#configs:
localIp='10.10.40.145'  ##
ports=[7001,7002]       ##
zkServers='192.168.110.125:8998'    ##
zkTimeoutSec=10
zkRootPath='/RedisHashWorkers'

redisCli='/usr/local/bin/redis-cli'
checkIntervalSec=2
checkTimeoutSec=5

#Node Settings
RoleName="Test2"            ##
Policy="CnstHashByZK"       ##
SiteName=""
Weight="1000"
RouteValue="host=%s\r\nport=%d\r\nmaxWait=0\r\nrequestTimeout=1000"


