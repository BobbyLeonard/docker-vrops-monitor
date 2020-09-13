import os
import requests
import getpass
import re
import time
import json
import socket
import psutil
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import ntforg
from pysnmp.proto.api import v2c

import configparser
userConfig = configparser.ConfigParser()
userConfig.read('envvars.txt')

def getUptime():
    p = psutil.Process()
    nowtime = round(time.time())
    boottime = round(psutil.boot_time())
    uptime = nowtime - boottime
    uptime = str(int(uptime) * 100) # Standard is hundreths of second
    return uptime

def getCurrentTime():
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    return "Last checked : {}".format(current_time)

from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import ntforg
from pysnmp.proto.api import v2c


def sendTheTrap():
    uptime = getUptime()
    # Create SNMP engine instance with specific (and locally unique)
    # SnmpEngineId -- it must also be known to the receiving party
    # and configured at its VACM users table.
    snmpEngine = engine.SnmpEngine(
        snmpEngineID=v2c.OctetString(hexValue='0102030405060708')
    )

    # Add USM user
    config.addV3User(
        snmpEngine, userConfig['DEFAULT']['SNMPUSER'],
        config.usmHMAC128SHA224AuthProtocol, userConfig['DEFAULT']['SNMPAUTH'],
        config.usmAesCfb192Protocol, userConfig['DEFAULT']['SNMPPRIV']
    )

    config.addTargetParams(snmpEngine, userConfig['DEFAULT']['SNMPAUTH'], userConfig['DEFAULT']['SNMPUSER'], 'authPriv')

    # Setup transport endpoint and bind it with security settings yielding
    # a target name
    config.addTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpSocketTransport().openClientMode()
    )

    config.addTargetAddr(
        snmpEngine, 'my-nms',
        udp.domainName, (userConfig['DEFAULT']['SNMPMANAGERIP'], int(userConfig['DEFAULT']['SNMPMANAGERPORT'])),
        userConfig['DEFAULT']['SNMPAUTH'],
        tagList='all-my-managers'
    )

    # Specify what kind of notification should be sent (TRAP or INFORM),
    # to what targets (chosen by tag) and what filter should apply to
    # the set of targets (selected by tag)
    config.addNotificationTarget(
        snmpEngine, 'my-notification', 'my-filter', 'all-my-managers', 'trap'
    )

    # Allow NOTIFY access to Agent's MIB by this SNMP model (3), securityLevel
    # and SecurityName
    config.addContext(snmpEngine, '')
    config.addVacmUser(snmpEngine, 3, userConfig['DEFAULT']['SNMPUSER'], 'authPriv', (), (), (1, 3, 6), 'aContextName')

    # *** SNMP engine configuration is complete by this line ***

    # Create Notification Originator App instance.
    ntfOrg = ntforg.NotificationOriginator()

    # Build and submit notification message to dispatcher
    ntfOrg.sendVarBinds(
        snmpEngine,
        # Notification targets
        'my-notification',  # notification targets
        None, 'aContextName',  # contextEngineId, contextName
        # var-binds
        [
            ((1, 3, 6, 1, 2, 1, 1, 3, 0), v2c.OctetString(uptime)),
            ((1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0), v2c.ObjectIdentifier((1, 3, 6, 1, 6, 3, 1, 1, 5, 1))),
            ((1, 3, 6, 1, 2, 1, 1, 5, 0), v2c.OctetString(socket.getfqdn())),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 10, 0), v2c.OctetString('Application')),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 11, 0), v2c.OctetString('Performance')),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 12, 0), v2c.OctetString('critical')),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 19, 0), v2c.OctetString('health')),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 20, 0), v2c.OctetString('vROpsExternalMonitorService.py')),
            ((1, 3, 6, 1, 4, 1, 6876, 4, 50, 1, 2, 50, 0), v2c.OctetString('vROps services are having issues, please check nodes'))
        ]
    )

    print('Notification is scheduled to be sent')

    # Run I/O dispatcher which would send pending message and process response
    snmpEngine.transportDispatcher.runDispatcher()


from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

RED  = '\033[91m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
BLUE='\33[44m'
BOLD = '\033[1m'
FFORMAT = '\033[0m'

headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
AuthInfo = {}


def acquireToken():
  #Token Request & Parsing
  TokenEndpoint="api/auth/token/acquire"
  URL=FQDN + TokenEndpoint
  r = requests.post(URL, json=AuthInfo, headers=headers, verify=False)
  output = r.text
  vROpsToken=output.split(',')[0].split(':', 1)[1][1:-1]

  #Add the Authorization Token to the header
  headers["Authorization"] = "vRealizeOpsToken "+vROpsToken
  print()
  print(headers["Authorization"])
  print()


def clearScreen():
  time.sleep(1)
  os.system('clear')
  purposeStr = 'vROps External Monitor Service'
  print(len(purposeStr) * '~' + '\n' + BOLD + purposeStr + FFORMAT + '\n' + len(purposeStr) * '~')


def GET():
    clearScreen()
    APIEndpoint = 'api/deployment/node/services/info'
    URL=FQDN + APIEndpoint
    r = requests.get(URL, headers=headers, verify=False)
    if str(r.status_code)[0] == '2':
        splitResponse(r.text)
    else:
        print(getCurrentTime())
        print('vROps resposnded with {}'.format(str(r.status_code)))
        if str(r.status_code) == '401':
          print('Asking for new token using credentials entered earlier')
          headers["Authorization"] = ""
          acquireToken()
        sendTheTrap()
        time.sleep(1)


def splitResponse(output):
    CountServices=0
    for item in output.split(']'):
        for value in item.split(','):
            if len(value) > 0:
                if re.search('"details":', value):
                    if not re.match(r'"details":"Success', value):
                        print(value[:-1])
                    else:
                        CountServices+=1
    if CountServices == 9:
        print(getCurrentTime())
        print('No issues, checking again in 30 secs')
        time.sleep(30)
    else:
        print(getCurrentTime())
        print('Panic Stations, send the trap !')
        sendTheTrap()
        time.sleep(10)

clearScreen()
FQDN=userConfig['DEFAULT']['VROPSFQDNIP']
print(FQDN)
FQDN="https://" + FQDN + "/suite-api/"
print(FQDN)
username=userConfig['DEFAULT']['VROPSAPIUSER']
print(username)
password=userConfig['DEFAULT']['VROPSAPIPASSWD']
print(password)
AuthInfo["username"] = username
AuthInfo["password"] = password
print(AuthInfo)
acquireToken()
while True :
    try:
        GET()


    except Exception as e:
        print(e)
        time.sleep(1)


