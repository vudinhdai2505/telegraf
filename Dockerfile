FROM telegraf:1.23-alpine
RUN apk add --no-cache python3 py3-pip
RUN pip install kubernetes && pip install schedule
COPY . .
CMD ["python3", "discovery.py"]