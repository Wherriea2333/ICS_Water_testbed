#!/bin/bash
(
cd "OpenPLC_v3" || exit 1
# check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
# create the docker network
sudo docker network inspect swat || sudo docker network create --subnet 172.18.0.0/16 --driver bridge swat

for i in {11..16}
do
  sudo docker build -t plc"$i":oplcv3
  sudo docker run --net swat --ip 172.18.0."$i" -d --rm --privileged -p 100"$i":8080 plc"$i":oplcv3
done
)
