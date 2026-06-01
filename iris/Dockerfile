FROM intersystems/irishealth-community:latest-cd

COPY . /tmp/iris/

WORKDIR /tmp/iris   

ENV IRISINSTALLDIR=/usr/irissys
ENV PATH="${PATH}:${IRISINSTALLDIR}/bin"
ENV PYTHONPATH="${IRISINSTALLDIR}/lib/python"
ENV IRISNAMESPACE=USER
ENV IRISUSERNAME=SuperUser
ENV IRISPASSWORD=SYS

COPY ./iris.script /home/irisowner/iris.script
COPY ./fhirdata /tmp/fhirdata

RUN mkdir -p /home/irisowner/dev
WORKDIR /home/irisowner/dev
COPY . .



RUN iris start IRIS \
    && iris session IRIS < /home/irisowner/iris.script\ 
    && iris stop IRIS quietly