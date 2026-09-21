*This project has been created as part of the 42 curriculum by dievarga*

# Call Me Maybe

## Description

Call Me Maybe is an object oriented Python 

## Instructions

### Makefile targets

- make install      : create the virtual environment and install dependencies
- make run          : run the project with a map file
- make debug        : run the project under pdb pythons debugger
- make clean        : remove caches and temp files
- make lint         : run flake8 and mypy
- make lint-strict  : execute the commands flake8 . and mypy . --strict

### Installation

When preparing the uv package manager to work with this project and its dependencies
as well as the llm sdk the following commands were used:
uv init --no-readme --app
uv add pydantic numpy
uv add --editable ./llm_sdk

Then to install the same dependencies in another machine and test the program:
make install

### Debugging
Using make debug' we got access to pythons debugger to examine the program:
- n (Next): Executes the current line and moves to the next line
- s (Step): Steps inside a function call
- c (Continue): Lets the program run normally until it hits a crash or finishes
- p <variable> (Print): Displays the live contents of any variable
- l (List): Prints the surrounding lines of code
- q (Quit): Instantly terminates the debugger

### Execution

make run - executes program and it also installs dependencies if missing.


## Resources

- 

### AI usage

AI (Claude & Gemini) were used to:
- 

## Algorithm


### Performance

