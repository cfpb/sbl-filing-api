FROM locustio/locust

COPY ./locust_scripts ./locust_scripts
COPY ./configs/filing-api.conf ./filing-api.conf
COPY ./run_locust.sh /usr/local/bin/

RUN pip install python-keycloak httpx
RUN mkdir /home/locust/reports
RUN mkdir /home/locust/sblars

EXPOSE 8089
EXPOSE 5557

ENTRYPOINT [ "run_locust.sh" ]