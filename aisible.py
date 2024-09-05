import argparse
import os
import sys
import time
from typing import List, Dict
import getpass
import configparser

import ansible_runner
import anthropic
from openai import OpenAI
import google.generativeai as genai

default_system_message = """You are an expert DevOps engineer specializing in analyzing Ansible outputs. Your task is to provide concise, insightful summaries of Ansible command or playbook results. Focus on identifying patterns, outliers, and potential issues that would be most relevant to system administrators and DevOps teams.
When analyzing outputs, consider the following aspects:

Overall execution status
Key metrics or data points
Version information (if present)
Node types and their characteristics
Outliers and deviations
Notable patterns in the data

Tailor your analysis to the specific type of Ansible command or playbook run. For infrastructure checks, focus on system health and consistency. For deployment tasks, emphasize success rates and any failed steps. For configuration management, highlight any drift or unexpected states.
Always conclude with a brief overall assessment and suggest areas that might need further investigation or action."""

default_user_message_template = """Analyze the following Ansible output:

Ansible Command/Playbook:
{ansible_command}

Ansible Output:
{ansible_output}

Provide a concise summary formatted as output of command line tool. For all variations and deviations always include host names or ranges of host names. Ensure all hosts mentioned in the output are included in your analysis."""


def parse_ansible_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ansible ad-hoc command and analyze output with LLM.")
    parser.add_argument('pattern', help="Host pattern")
    parser.add_argument('-i', '--inventory', required=True, help="Specify inventory file path")
    parser.add_argument('-m', '--module', default='command', help="Module name to execute")
    parser.add_argument('-a', '--args', help="Module arguments")
    parser.add_argument('-u', '--user', help="Connect as this user")
    parser.add_argument('-b', '--become', action='store_true', help="Run operations with become")
    parser.add_argument('-K', '--ask-become-pass', action='store_true', help="Ask for privilege escalation password")
    parser.add_argument('-c', '--config', default='aisible.cfg', help="Path to config file")
    return parser.parse_args()


def get_absolute_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(os.getcwd(), path))


def load_config(config_path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def run_ansible_command(args: argparse.Namespace) -> str:
    if ',' in args.inventory:
        inventory = list(args.inventory.split(','))
    else:
        inventory = get_absolute_path(args.inventory)

    print(f"Executing Ansible command with module '{args.module}' and args '{args.args}'", file=sys.stderr)
    print(f"Inventory file: {inventory}", file=sys.stderr)
    print(f"Host pattern: {args.pattern}", file=sys.stderr)
    start_time = time.time()

    extra_vars = {}
    if args.user:
        extra_vars['ansible_user'] = args.user
    if args.become:
        extra_vars['ansible_become'] = 'yes'
    if args.ask_become_pass:
        extra_vars['ansible_become_pass'] = getpass.getpass("BECOME password: ")

    runner = ansible_runner.run(
        private_data_dir='/tmp',
        inventory=inventory,
        playbook=None,
        module=args.module,
        module_args=args.args,
        host_pattern=args.pattern,
        extravars=extra_vars,
        verbosity=0,
    )

    end_time = time.time()
    print(f"Command execution took {end_time - start_time:.2f} seconds", file=sys.stderr)

    all_output = []
    for event in runner.events:
        if event['event'] in ('runner_on_ok', 'runner_on_failed', 'runner_on_unreachable'):
            host = event['event_data']['host']
            result = event['event_data']['res']
            status = 'CHANGED' if result.get('changed', False) else 'SUCCESS'
            if event['event'] == 'runner_on_failed':
                status = 'FAILED'
            if event['event'] == 'runner_on_unreachable':
                status = 'UNREACHABLE'
            output = f"{host} | {status} | rc={result.get('rc', 'N/A')} >>\n"
            if status == 'UNREACHABLE':
                output += "UNREACHABLE!" + result.get('msg', '') + "\n"
            output += result.get('stdout', '') + '\n'
            if result.get('stderr'):
                output += "STDERR: " + result.get('stderr') + '\n'
            all_output.append(output)

    return '\n'.join(all_output)


def prepare_llm_input(ansible_command: str, ansible_output: str, config: configparser.ConfigParser) -> dict:
    if 'prompts' in config and 'system_message' in config['prompts'] and config['prompts']['system_message']:
        system_message = config['prompts']['system_message']
    else:
        system_message = default_system_message
    if 'prompts' in config and 'user_message_template' in config['prompts'] and config['prompts']['user_message_template']:
        user_message_template = config['prompts']['user_message_template']
    else:
        user_message_template = default_user_message_template

    system_message = system_message
    user_message = user_message_template.format(
        ansible_command=ansible_command,
        ansible_output=ansible_output
    )
    if 'prompts' in config and config['prompts']['request_specific_user_message_addon']:
        user_message += f"\n\n{config['prompts']['request_specific_user_message_addon']}"

    return {
        "system": system_message,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }


def call_anthropic_api(input_data: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0,
            system=input_data["system"],
            messages=input_data["messages"]
        )
        llm_response = response.content
        text_content = llm_response[0].text if llm_response and hasattr(llm_response[0],
                                                                        'text') else "No content available"
        return text_content.replace('\\n', '\n')
    except Exception as e:
        return f"Error calling Anthropic API: {str(e)}"


def call_gpt_api(input_data: dict) -> str:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": input_data["system"]},
                {"role": "user", "content": input_data["messages"][0]["content"]}
            ]
        )
        return response.choices[0].message.content.replace('\\n', '\n')
    except Exception as e:
        return f"Error calling GPT API: {str(e)}"


def call_gemini_api(input_data: dict) -> str:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(
            f"System: {input_data['system']}\n\nUser: {input_data['messages'][0]['content']}"
        )
        return response.text.replace('\\n', '\n')
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"


def choose_api() -> str:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    available_apis = []
    if anthropic_key:
        available_apis.append('anthropic')
    if openai_key:
        available_apis.append('gpt')
    if gemini_key:
        available_apis.append('gemini')

    if not available_apis:
        raise ValueError("No API keys found. Please set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY environment variables.")

    if len(available_apis) > 1:
        print("Available APIs:", ", ".join(available_apis))
        choice = input(f"Which API would you like to use? ({'/'.join(available_apis)}): ").lower()
        while choice not in available_apis:
            choice = input(f"Invalid choice. Please enter one of {', '.join(available_apis)}: ").lower()
        return choice
    else:
        return available_apis[0]


def main():
    args = parse_ansible_args()
    config = load_config(args.config)

    try:
        api_choice = choose_api()
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

    ansible_output = run_ansible_command(args)

    # print("Ansible Output:", file=sys.stderr)
    # print(ansible_output, file=sys.stderr)

    ansible_command = f"ansible {args.pattern} -i {args.inventory} -m {args.module}"
    if args.args:
        ansible_command += f" -a '{args.args}'"
    if args.user:
        ansible_command += f" -u {args.user}"
    if args.become:
        ansible_command += " -b"
    if args.ask_become_pass:
        ansible_command += " -K"

    llm_input = prepare_llm_input(ansible_command, ansible_output, config)
    # print("\nLLM Input:")
    # print(llm_input)

    if api_choice == 'anthropic':
        llm_response = call_anthropic_api(llm_input)
    elif api_choice == 'gpt':
        llm_response = call_gpt_api(llm_input)
    else:
        llm_response = call_gemini_api(llm_input)

    print("\nLLM Response:")
    print(llm_response)


if __name__ == "__main__":
    main()
