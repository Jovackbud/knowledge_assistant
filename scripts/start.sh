#!/bin/bash

# Initialize databases and sync documents
python scripts/initialize.py

# Start Streamlit
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0