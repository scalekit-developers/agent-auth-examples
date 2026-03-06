# Agent Guidelines

Keep this repository clean, easy to browse, and navigate by following these rules:

## Repository Structure

- Use the existing `python/` and `javascript/` directories for language-specific examples
- Group related examples by feature or use case
- Keep the directory structure flat and shallow (max 3 levels deep)

## File Organization

- Name files descriptively using kebab-case (e.g., `basic-auth-example.js`)
- One example per file when possible
- Add a `README.md` in each subdirectory explaining what's inside
- Keep related files together in the same directory

## Documentation

- Every example file should have a clear comment at the top explaining:
  - What the example demonstrates
  - How to run it
  - Required dependencies or setup
- Keep documentation concise and up-to-date
- Use code blocks with language syntax highlighting

## Code Style

- Follow language-specific conventions (PEP 8 for Python, standard JS/TS conventions)
- Write clean, readable code with clear variable names
- Add comments only when the code isn't self-explanatory
- Keep functions small and focused on a single purpose

## Commits

- Write clear, descriptive commit messages (max 50 characters for title)
- Use imperative mood ("Add example" not "Added example")
- Commit related changes together
- Don't commit temporary files, debugging code, or unused imports

## Before Submitting

- Run linters and formatters for the language you're working in
- Test that your examples actually work
- Remove any hardcoded credentials or secrets
- Ensure all new files have proper descriptions

## What NOT to Do

- Don't create deeply nested directories
- Don't add unnecessary dependencies
- Don't commit `.env` files or secrets
- Don't leave commented-out code in examples
- Don't create duplicate or redundant examples