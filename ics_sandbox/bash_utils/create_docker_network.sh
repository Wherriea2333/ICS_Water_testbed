#!/bin/bash
(
cd "OpenPLC_v3_customized" || exit 1

# check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# create the docker network
sudo docker network inspect swat || sudo docker network create --subnet 172.18.0.0/16 --driver bridge swat

#   build and run the plcs
for i in {11..16}
do
  sudo docker build -t plc"$i":oplcv3 .
  sudo docker run --net swat --ip 172.18.0."$i" -d --rm --privileged -p 100"$i":8080 plc"$i":oplcv3
done
)
#  build and run the simulator
(
cd sim || exit 1
sudo docker build -t sim:sim .
sudo docker run --net swat --ip 172.18.0.10 -d --rm --privileged sim:sim
)
