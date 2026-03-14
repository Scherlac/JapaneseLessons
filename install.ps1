# Installation script for Japanese Lesson Generator
# Run this script to install all dependencies for the full functionality

Write-Host "Installing dependencies for Japanese Lesson Generator..."

# Activate conda base environment
conda activate base

# Install Python dependencies from pyproject.toml
Write-Host "Installing Python dependencies..."
pip install -e .[all]

# Install ffmpeg via conda
Write-Host "Installing ffmpeg..."
conda install -c conda-forge ffmpeg -y

Write-Host "Installation complete!"
Write-Host "You can now run the full video pipeline and LLM features."