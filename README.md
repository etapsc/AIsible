# Aisible

Aisible is an advanced DevOps tool that combines the power of Ansible with AI-driven analysis. It runs Ansible ad-hoc commands or playbooks and uses Language Models (LLMs) to provide insightful summaries and analyses of the output.

## Purpose

Aisible aims to streamline DevOps workflows by:

1. Executing Ansible commands or playbooks across your infrastructure
2. Analyzing the output using state-of-the-art Language Models
3. Providing concise, actionable insights about your systems' state

This tool is particularly useful for:
- Quick system health checks
- Identifying outliers and potential issues in your infrastructure
- Summarizing complex Ansible outputs for easier understanding

## Installation

To install Aisible, you can use pip:

```bash
pip install aisible
```

Ensure you have Python 3.7 or later installed on your system.

## Configuration

Aisible uses a configuration file ('aisible.cfg') to customize its behavior. By default, it looks for this file in the current directory, but you can specify a different path using the '-c' or '--config' option.

Example 'aisible.cfg':

```ini
[prompts]
system_message = Your custom system message here.
user_message_template = Your custom user message template here.
request_specific_user_message_addon = Additional instructions for the LLM.
```

If no custom prompts are specified in the configuration file, Aisible uses the default prompts.
The default prompts are designed to provide comprehensive and relevant analysis of Ansible outputs without requiring any additional configuration. However, you can customize them in the configuration file to better suit your specific needs.
Or ypu can improve prompts for your specific environment by specifying `request_specific_user_message_addon` in the configuration file.

## Usage

Aisible can be used to run Ansible ad-hoc commands or playbooks:

```bash
aisible [pattern] -i INVENTORY [options]
```

### Options:

- '-i, --inventory': Specify inventory file path (required)
- '-m, --module': Module name to execute (for ad-hoc commands)
- '-p, --playbook': Path to Ansible playbook file
- '-a, --args': Module arguments (for ad-hoc commands)
- '-u, --user': Connect as this user
- '-b, --become': Run operations with become (privilege escalation)
- '-K, --ask-become-pass': Ask for privilege escalation password
- '-c, --config': Path to config file (default: aisible.cfg)

### Environment Variables:

Set at least one of the following API keys as environment variables:

- 'ANTHROPIC_API_KEY': For using Anthropic's Claude
- 'OPENAI_API_KEY': For using OpenAI's GPT
- 'GEMINI_API_KEY': For using Google's Gemini

## Examples

1. Run an ad-hoc command to check disk usage:

```bash
aisible all -i inventory.yml -m shell -a "df -h"
```

2. Execute a playbook:

```bash
aisible all -i inventory.yml -p my_playbook.yml
```

3. Check the status of a service with privilege escalation:

```bash
aisible webservers -i inventory.yml -m systemd -a "name=nginx state=started" -b -K
```

4. Use a custom configuration file:

```bash
aisible all -i inventory.yml -m ping -c /path/to/custom_config.cfg
```

## Output

Aisible will execute the Ansible command or playbook and then provide an AI-generated analysis of the output. The analysis will include:

- Overview of the execution status
- Key metrics and data points
- Identification of outliers or deviations
- Notable patterns in the data
- Suggestions for further investigation or action

## Examples with output

```bash
aisible -i hosts.yaml all -p system_check.yml
```

Output:
```plaintext
System Check Summary
====================

Hosts: 15 (host01 to host15)

SSH Connections:
  3 connections: 14 hosts
  5 connections: host12

Ubuntu Version:
  All hosts: Ubuntu 22.04.4 LTS

Nginx Status:
  All hosts: Active

Security Messages:
  All hosts: No critical security messages found
  
Disk Usage:
  Root partition (/dev/sda3):
    Size: 1.6T
    Used: 83G - 101G (6-7%)
  Boot partition (/dev/sda2):
    Size: 2.0G
    Used: 170M (10%)

Memory Usage:
  Total: 47Gi on all hosts
  Used:
    10Gi - 20Gi: 7 hosts
    21Gi - 30Gi: 6 hosts
    34Gi: host05
  Free:
    10Gi - 20Gi: 3 hosts
    21Gi - 30Gi: 9 hosts
    31Gi - 34Gi: 3 hosts

Notes:
- All hosts running Ubuntu 22.04.4 LTS
- Nginx active on all hosts
- Disk usage consistent across hosts, low utilization
- Memory usage varies, with host05 showing highest usage

Recommendations:
1. Investigate higher SSH connections on host12
2. Monitor memory usage on host05

This summary provides an overview of the system check results, highlighting key findings and potential areas for further investigation.
```


## Contributing

Contributions to Aisible are welcome! Please refer to the CONTRIBUTING.md file for guidelines on how to contribute to this project.

## License

Aisible is released under the MIT License. See the LICENSE file for more details.
