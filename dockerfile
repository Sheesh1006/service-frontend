FROM python:3.13

RUN mkdir frontend

COPY . /frontend

EXPOSE 8000
	
CMD ["python", "/frontend/main.py"]
