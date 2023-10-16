```
• Namespaces=32 
• Unscheduled namespaces=18
• Backup active=16 
• Completed=14
• Errors=1
  bck-black-arrow-service
• Wrn=1
  bck-black-arrow-service
Number of backups in warning period=1 [expires day less than 28d]
```
```
Backup details [16/32]:
bck-attila
   end at=2023-10-14T00:15:55Z
   expire=28d
   status=Completed

bck-black-arrow-service
   end at=2023-09-25T17:20:56Z
   expire=9d**WARNING
   status=PartiallyFailed
  error=4   warning=4 
bck-rome-broker
   end at=2023-10-14T00:21:07Z
   expire=28d
   status=Completed

bck-rome-operator
   end at=2023-10-14T00:25:57Z
   expire=28d
   status=Completed

bck-test-ingress
   end at=2023-10-14T00:30:57Z
   expire=28d
   status=Completed

bck-wh
   end at=2023-10-14T00:35:53Z
   expire=28d
   status=Completed

bck-wh-public
   end at=2023-10-14T00:40:53Z
   expire=28d
   status=Completed

bck-wh-system
   end at=2023-10-14T00:46:02Z
   expire=28d
   status=Completed

bck-k8s-dashboard
   end at=2023-10-14T00:51:01Z
   expire=28d
   status=Completed

bck-mts-system
   end at=2023-10-14T00:55:54Z
   expire=28d
   status=Completed

bck-nfs-test
   end at=2023-10-14T01:00:54Z
   expire=28d
   status=Completed

bck-nodered-test
   end at=2023-10-14T01:06:01Z
   expire=28d
   status=Completed

bck-ha
   end at=2023-10-14T01:10:54Z
   expire=28d
   status=Completed

bck-ha-relay
   end at=2023-10-14T01:15:53Z
   expire=28d
   status=Completed

bck-test-ee3
   end at=2023-10-14T20:03:49Z
   expire=29d
   status=Failed

bck-velero
   end at=2023-10-14T01:27:20Z
   expire=28d
   status=Completed
```
```
Namespace without active backup [18/32]:
 defaultX
 bs-local-service
 goldrake-fe
 shark-attack
 k8s-test
 kenshiro-zapp
 kenshiro-develop
 kenshiro-develop-frontend
 kenshiro-htc
 logger-all
 mazinga-test
 mazinga-elk
 mazinga-monitoring
 monitoring
 monitoring-prometheus
 monstache
 vr46-develop
 postfix-relay
```