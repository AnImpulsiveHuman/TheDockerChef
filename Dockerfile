FROM ubuntu

RUN apt-get update -y TEMP && rm -rf /var/lib/apt/lists/*
