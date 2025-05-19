#!/bin/bash

# Initialize databases
python src/database_utils.py

# Sync documents
python src/document_updater.py

# Start Streamlit
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0