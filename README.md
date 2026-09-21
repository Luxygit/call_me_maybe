*This project has been created as part of the 42 curriculum by dievarga*

# Call Me Maybe

## Description

Call Me Maybe is an object oriented Python program that helps a small AI model
Qwen3-0.6B write near-perfect computer data. Small AI models make many
mistakes and write broken sentences, so with this tool the model is helped
step by step to do so following some strict rules to block any words or 
characters that break standard JSON file format response.

## Instructions

### Makefile targets

- make install      : create the virtual environment and dependencies via uv
- make run          : run the main program with the test data files
- make debug        : run the project under pdb pythons debugger
- make clean        : remove caches and temp files
- make lint         : run flake8 and mypy
- make lint-strict  : execute the commands flake8 and mypy with --strict flag

### Installation
When setting up the uv package manager to work with this project and its
dependencies as well as the llm sdk the following commands were used:
uv init --no-readme --app       : creates a python project structure
uv add pydantic numpy           : adds dependencies to the project
uv add --editable ./llm_sdk     : 

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

make run - executes program with default test file paths.
or
uv run python -m src [–functions_definition <function_definition_file>]
[–input <input_file>] [–output <output_file>]
We connect to the provided AI tool using Small_LLM_Model. This allows our
program to read the AI's internal mathematical thoughts (logits) and give
it the history of what has been typed so far.

## Resources
### AI usage
AI (Claude & Gemini) were used to:
- Figure out a way to format the output JSON style
- Fixing typos and edge cases
- Handle all possible Exceptions

## Algorithm
The program uses a technique known as constrained decoding, which instead of
letting the AI make the entire output layout freely, it guides it char by char.
To prevent chat bot responses, it uses a technique called Pre-typing.
I stablished a starter context string `[{"prompt": "...", "name": "` directly
into the AI's active history array. This instantly forces the AI to start
typing out a valid function name next.
Our vocabulary engine loads the AI's vocab.json dictionary. It builds an index
mapping so we can translate numbers back into string text instantly. This lets
us check which letters are hidden behind the AI's number tokens.
Every time the AI wants to choose the next word, it calculates scores for
all words in its vocabulary, then the program uses a fast Numpy Matrix Mask
to intercept all the words that would break the JSON structure and 
assigns their value to -inf forcing AI to avoid them.
Once the text generation finishes, the text is fed into a safe JSON sandbox
utilizing a `try-except`, it attemps to read the string with json.loads().

## Design Decisions
- Flat app structure. pyproject.toml is a simple flat app instead of a complex
compiled library.
- By building via uv init -app instead of the default --lib that would create
a library package expecing to be bundled up, compiled and shared expecting
a very strict file layout and naming.
- Running uv add llm_sdk --editable makes it so that the sdk is dynamically 
run in case any of its files changes. It also avoids linter issues with a 
cached version of a static local dependency.
- -inf logit masking for word filtering.
- numpy float32 int32 for fast lookups

## Performance Analysis
- Simple direct dictionary lookups, therefore the program is quite fast and
gives an output in a few seconds.
- MaskingEngine uses an optimised 32 bit float inside clean_logits to
manage token lookups. Since the AI can go through a list of thousands of 
numbers, one number for every word in its dictionary, that can make execution
very slow, but by turning the raw data list into a numpy continous mem array
float32 with int32 ID numbers making the process of looking up tokens
much faster.

## Challenges Faced
- Figuring out how to intercept the AI logits and understanding how to 
make it give an structured output in a specific format.

## Example usage
The next command can be run with our own test files and the output should be
in a JSON output format.
uv run python -m src --functions_definition data/input/functions_definition.json --input data/input/function_calling_tests.json --output data/output/function_calling_results.json
