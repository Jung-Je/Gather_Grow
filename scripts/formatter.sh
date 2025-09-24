echo "Running isort..."
uv run isort .
echo "Running black..."
uv run black .
echo "Done"