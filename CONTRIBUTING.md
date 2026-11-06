# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `dev`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using black).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Run tests and validation

Use Python 3.14, matching CI. From the repository root, create and activate a
virtual environment, then install and run the test tools:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install tox==4.32.0 tox-gh-actions==3.5.0
tox
```

Tox runs pytest, Ruff lint and format checks, and mypy in isolated environments.
The pytest environment disables external sockets, allowing only loopback access
for tests. For focused runs, use `tox -e py314 -- tests/test_init.py --no-cov`
or run Ruff directly with `ruff check --no-fix .` and `ruff format --check .`.
For a pull-request base SHA, validate changed SPEC-001 artifacts locally with
`python check_spec_artifacts.py --base-ref <PR-base-sha>`.
HACS and hassfest validation run in the **Validation** GitHub Actions workflow;
start it from the Actions tab with **Run workflow** when needed.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
