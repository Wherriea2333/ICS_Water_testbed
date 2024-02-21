#!/bin/bash
(
cd "OpenPLC_v3" || exit 1
# check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
# create the docker network
docker network insprct swat > dev/null || docker network create --subnet 172.18.0.0/16 --driver bridge swat

for i in {1..6}
do
    docker run --net swat --ip 172.18.0."$i" -it --rm --privileged -p 70"$i":8080 plc"$i":oplcv3 &
done
)