# Publishing

## Build Locally

```shell
python -m pip install -e ".[dev]"
python -m build
python -m twine check dist/*
```

## TestPyPI

```shell
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple yedipy
```

## PyPI Trusted Publishing

The included GitHub Actions workflow publishes when a GitHub release is published. Before using it:

1. Push this directory to its intended GitHub repository.
2. Configure that repository and the `publish.yml` workflow as a trusted publisher in PyPI, or create a pending publisher for the project name `yedipy`.
3. Create and publish a GitHub release with the intended version tag.

The workflow builds the distribution, checks it with Twine, and uploads it using GitHub's OpenID Connect identity. It does not require a PyPI token in the repository.