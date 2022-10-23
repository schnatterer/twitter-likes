# When upgrading, upgrade path in final image as well
FROM python:3.9-slim AS build-env
RUN apt-get update
RUN apt-get -y upgrade

RUN pip3 install --upgrade pip
COPY requirements.txt .
RUN pip install -r ./requirements.txt

#FROM gcr.io/distroless/python3:nonroot
# Pin to repo digest to avoid failing builds due to new minor version
# When upgrading, make sure target path contains proper python minor version (e.g. "python3.9/")
FROM gcr.io/distroless/python3@sha256:07beba7c707b5d5f711847969c55692c10b771e58b0674b90a4776ae2ebd2288
WORKDIR /cwd
ENV PYTHONPATH=/usr/local/lib/python3.9/site-packages

COPY --from=build-env /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . /scripts