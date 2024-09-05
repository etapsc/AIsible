# Aisible

Aisible is a tool that runs Ansible commands and analyzes the output using various Language Models (LLMs) such as OpenAI's GPT, Anthropic's Claude, and Google's Gemini.

## Installation

```bash
pip install aisible
```

## Usage
```bash
aisible [pattern] -i [inventory] -m [module] -a [args] [options]
```

For more information on usage, run:
```bash
aisible --help
```

## Configuration
Aisible uses a configuration file (aisible.cfg) for customizing prompts. You can specify the path to this file using the -c or --config option.

## API Keys
Aisible supports multiple LLM APIs. Set the appropriate environment variable for the API you want to use:

* Anthropic: ANTHROPIC_API_KEY 
* OpenAI: OPENAI_API_KEY 
* Google Gemini: GEMINI_API_KEY

## License
This project is licensed under the MIT License.
