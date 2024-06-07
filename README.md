# Automated Coding Agents Starter Kit
## w/ CrewAI and Github issues


### 1. Limitations
1. This is not production tested
2. It is optimized for the following directory structure:
   ```
    - favicon.png
    - package.json
    - public
        - index.htm
        - favicon.png
   - src
        - App.css
        - App.js
        - index.css
      	- index.js

   ```


### 2. Workflow
... TODO


### 3. Running
1. `cp env.template .env`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip3 install -r requirements.txt`
5. `python3 start.py` to kick off the agent tasks, which will be dictated by the state of the Github repository according to `Workflow` above


### 4. Developing
1. [Check out the first Demo project](https://github.com/kvnn/AIAgentsStarterKit-DemoProject-01).
2. Its assumed that if you have an `OPENROUTER_API_KEY` in `.env` and you want to use OpenRouter. 
3. Otherwise, you want to use OpenAI and `OPENAI_API_KEY` is required in `.env`
4. See `.env` (remember you need to create .env from env.template)


### 5. Vision
1. A simple, configurable human-steered A.I. web-dev GUI


`pip install agents-starter-kit`, Open Interpreter


### 6. Design Decisions
1. CrewAI is the most concise, effective agent projects we have found, and it is very wells supported by the founder & his company. So we use it instead of Autogen
2. Github is ubiquitous , reliable and fulfills all essential project-management functionality . So we use Github Issues, Pull Requests, Actions, etc.
3. OpenInterpreter should be considered (e.g. for QA Agents)


TODO:
- [ ] make "Workflow" configurable via config.yml