# GenAI Telegram Bot
A single plaform with multiple GenAI models via Telegram bot. Allowing user to utilise different models and version in single platform.

This repo is a personal project to build up to expand knowledge with API and LLM.   

*Have fun and continue building.*

## Features
- Allow user to select the multiple models and version. [User can change or add more by editing the configuration]
    - Claude (v3.5 Haiku and v3.7 Sonnet)
    - Deepseek (V3 & R1)
    - ChatGPT (o4 & o4-mini)

##  WIP
- [&check;] Add databases
- [&check;] Admin menu to allow for statistc (users, API cost, access control, etc)
- [&cross;] Add additional LLM models (Perplexity Sonar & Google Gemini)
- [&cross;] Add websearch function via GoogleSearch API
- [&cross;] Add basic agentic workflow & tools (multi-steps on thinking process & utilising available tools)
- [&cross;] Further enhancement

## Setup
- Prepare all relevant LLM API Keys 
- Create telegram bot via Telegram @BotFather
- Create .env file and store the your LLM & Telegram API keys *(take reference from example.env)*
- Change configuration in config file
    - Depending on what model you want to run, you can add or remove from *(config.py -> MODEL_CHOICE)*
- Run main.py
