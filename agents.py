from crewai import Agent, Task, Crew, Process

from llms import cto_llm, coder_llm


technology_preferences = '''
    We prefer to use a simple FastAPI backend that serves a React Native frontend with Mui.
    We accomplish this with the following files.
'''

# TODO: make this a setting of the target GITHUB repo
project_description = '''
    - `app.py` for the FastAPI backend.
    - `index.html` for the React Native frontend.
    - `public` directory for static assets.
    - `src/App.js` for the React Native frontend.
    - `src/index.js` for the React Native frontend.
'''

planner_task_expected_output = 'A collection of working python, javascript css and/or html files.'

def get_planner_task_description(prompt):
    return f'''
        Return the code that meets the requirements of the Issue:
        {prompt}
    '''

def get_coder_task_description(issue, cto_spec):
    return f'''
        You are tasked with implementing the solution for the following Github Issue:
        {issue.body}

        The CTO has provided the following technical spec and implementation plan:
        {cto_spec}

        Your goal is to create a pull request that fulfills the requirements outlined in the issue and adheres to the technical spec.
        Please make sure to:
        - Follow the company's technology preferences and best practices.
        - Provide clear and concise commit messages.
        - Write clean, maintainable, and efficient code.
        - Include necessary documentation and comments.
        - Reference the original GitHub issue in your pull request.
    '''

def get_coder_refactor_task_description(pull_request, cto_spec, refactor_feedback):
    return f'''
        You are tasked with refactoring the code for the following pull request:
        Pull Request: {pull_request.html_url}
        
        The CTO's technical spec and implementation plan:
        {cto_spec}
        
        Refactoring feedback:
        {refactor_feedback}
        
        Please update the code based on the provided feedback and best practices.
        Make sure to:
        - Address all the points mentioned in the refactoring feedback.
        - Follow the company's coding standards and guidelines.
        - Write clean, efficient, and maintainable code.
        - Update the pull request with the refactored code.
    '''

agent_instructor = Agent(
    role = "Coding-Agent Instructor",
    llm = cto_llm,
    allow_delegation = False,
    verbose = True,
    goal = f"""
        You will provide instructions to a Coding Agent . Give it coding instructions in plain English.

        The web application is organized like this:
        {project_description} .
        
    """,
    backstory = """
    """,
)

agent_coder = Agent(
    role = "Programmer",
    llm = coder_llm,
    allow_delegation = True,
    verbose = True,
    goal = f"""
        Return code that meets the requirements of the task. {technology_preferences}
        {technology_preferences}
    """,
    backstory = """
        You are an experienced Technical Lead with a strong background in software development and team management. 
        You have a Master's degree in Computer Science and have worked on numerous successful projects in your career.

        You have expertise in React Native, FastAPI, Postgres, git, bash, and ffmpeg. You are well-versed in the 
        company's technology stack and best practices, and you are committed to ensuring that the development team 
        delivers high-quality software solutions.

        Your role is to respond to Github feature requests or bug requests with code that meets the requirements.
        
        You value simplicity, elegance and practical, working solutions.
    """,
)