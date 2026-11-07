# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase. Read [AGENTS.md](AGENTS.md) for the S/M/L specification workflow, compatibility requirements, and project-specific verification guidance before starting feature work.

1. Fork the repo and create your branch from the target branch named by the issue or maintainer (roadmap work targets `test/all-features`).
2. If you've changed something, update the documentation.
3. Run the relevant tests and checks (`tox` runs pytest, Ruff lint/format checks, and mypy).
4. Open a draft pull request, wait for Actions and independent review, and merge only with maintainer approval.

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

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
