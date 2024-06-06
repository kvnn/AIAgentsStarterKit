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
1. Do we need the CTO?
   - Yes for any open Issues without Pull Requests ~(only the Human closes Issues)~ unless the last comment begins with "[cto]" ~(it will wait for the coder to respond)~
       <!-- 1. yes if there are no comments
       1. no if the comment says "[architect spec]" -->
2. Do we need the Coder?
   - Yes for any open PR (only the CTO closes Pull Requests) unless the comment begins with "[coder]" (it will wait for the human to merge the PR or a QA Agent to reply)
     - ** the Coder shouldn't try twice ~** the LLM can still provide multiple implementation options, but they'll be in a single comment~


### 3. Running
1. `cp env.template .env`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip3 install -r requirements.txt`
5. `python3 init_agents.py` to kick off the agent tasks, which will be dictated by the state of the Github repository according to `Workflow` above


### 4. Devloping
1. Its assumed that if you have an `OPENROUTER_API_KEY` in `.env` and you want to use OpenRouter. 
1. Otherwise, you want to use OpenAI and `OPENAI_API_KEY` is required in `.env`
1. See `.env` (remember you need to create .env from env.template)

TODO:
- [ ] make "Workflow" configurable via config.yml