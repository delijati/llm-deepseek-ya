pip install --upgrade build twine
rm -rf dist/ build/ *.egg-info/
python -m build
twine check dist/*
twine upload dist/*
git tag -a v2.0.1 -m "Release version 2.0.1 aka deepseek v4"
git push origin v2.0.1

