FROM python:3.10.20-slim

WORKDIR /imax

RUN pip3 install Pyro5
RUN pip3 install -U scikit-learn
RUN pip3 install pandas
RUN pip3 install notebook

COPY . .