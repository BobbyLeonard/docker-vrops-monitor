FROM python:3
WORKDIR /app
RUN mkdir log
COPY ./app /app
COPY ./envvars.txt /app
RUN pip install -r requirements.txt
ENV TERM=xterm
ENTRYPOINT [ "python","-u", "main.py" ]

