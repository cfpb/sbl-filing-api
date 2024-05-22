FROM locustio/locust

COPY ./locust_scripts ./locust_scripts
COPY ./configs/filing-api.conf ./filing-api.conf
COPY ./sblars ./sblars
COPY ./run_locust.sh /usr/local/bin/

RUN pip install python-keycloak
RUN mkdir /home/locust/reports

EXPOSE 8089
EXPOSE 5557

ENTRYPOINT [ "run_locust.sh" ]