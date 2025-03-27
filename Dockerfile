FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make port 7860 available to the world outside the container
EXPOSE 7860

# Command to run when the container starts
CMD ["python", "app.py"]