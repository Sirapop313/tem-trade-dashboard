#!/bin/bash
cd ~/Documents/tem-os/investing
streamlit run dashboard.py \
  --browser.gatherUsageStats false \
  --server.address 0.0.0.0
