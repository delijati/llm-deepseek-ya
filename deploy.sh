pip install --upgrade build twine
rm -rf dist/ build/ *.egg-info/
python -m build
twine check dist/*
twine upload dist/*
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

