FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app


RUN pip install --upgrade pip

COPY requirements.txt /app
# Install Streamlit
RUN pip install -r requirements.txt

COPY . /app

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]