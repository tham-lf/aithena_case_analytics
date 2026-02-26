#!/bin/bash

# Start the FastAPI backend in the background
echo "Starting FastAPI backend on port 8000..."
uvicorn api:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit dashboard on the port provided by Railway (or default to 8501)
echo "Starting Streamlit dashboard on port ${PORT:-8501}..."
streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
