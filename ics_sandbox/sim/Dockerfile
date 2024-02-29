FROM ubuntu:20.04
COPY physic_simulation .
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN pip3 install -r ./requirements.txt

ENTRYPOINT [ "python3" ]

CMD ["run.py","-c", "test.yml", "-v", "2", "-m", "proportional"]