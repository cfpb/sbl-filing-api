docker kill sbl-locust
docker container rm sbl-locust
docker build -t sbl-locust .
docker run -d -v ./reports:/home/locust/reports --name sbl-locust --network sbl-project_default --env-file ./configs/locust.env --env MODE=headless sbl-locust