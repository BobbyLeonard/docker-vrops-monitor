# docker-vrops-monitor

Install git and docker, make sure docker service is running.

`git clone https://github.com/BobbyLeonard/docker-vrops-monitor.git`

`cd docker-vrops-monitor/`

Edit `envvars.txt` to add required usernames, passwords etc.

SNMP Authorization uses SHA224, Privacy uses AES192

`docker build -t docker-vrops-monitor .`

You can now delete `envvars.txt`

`docker run --name docker-vrops-monitor -d  docker-vrops-monitor`

To check the container for errors : `docker logs docker-vrops-monitor

The default securityEngineId is 0102030405060708

If you require a differnet EngineID edit the following line in main.py before building.

`securityEngineId=v2c.OctetString(hexValue='0102030405060708')`
