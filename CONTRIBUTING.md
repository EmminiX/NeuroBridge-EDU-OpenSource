# Contributing to NeuroBridge EDU

We love your input! We want to make contributing to NeuroBridge EDU as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code follows the existing style guidelines.
6. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issue tracker](https://github.com/EmminiX/NeuroBridge-EDU-OpenSource/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/EmminiX/NeuroBridge-EDU-OpenSource/issues/new).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   cd python_backend && pip install -r requirements.txt
   ```
3. Copy environment files:
   ```bash
   cp .env.example .env
   cp python_backend/.env.example python_backend/.env
   ```
4. Start development servers:
   ```bash
   npm run dev:frontend  # Frontend on port 3131
   cd python_backend && python -m uvicorn main:app --reload --port 3939  # Backend
   ```

## Code Style

### Frontend (TypeScript/React)
- Use TypeScript for all new code
- Follow existing naming conventions
- Use functional components with hooks
- Maintain accessibility standards (WCAG 2.2 AA)

### Backend (Python)
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Maintain async/await patterns
- Write comprehensive docstrings

### Security Guidelines
- Never commit API keys or sensitive data
- Follow secure coding practices
- Validate all user inputs
- Use parameterized queries for database operations

## Testing

- Write unit tests for new functionality
- Ensure existing tests pass
- Test both frontend and backend components
- Include integration tests for API endpoints

## License

By contributing, you agree that your contributions will be licensed under its MIT License.