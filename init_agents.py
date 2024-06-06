from collections import namedtuple
import os

from github import Github, Auth
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()

Message = namedtuple('Message', ['role', 'content'])
gh_repo = None
gh_base_branch = os.environ.get('GH_BASE_BRANCH', 'main')
gh_access_token = os.environ.get('GH_ACCESS_TOKEN', '')
gh_repo_name = os.environ.get('GH_REPO_NAME', 'kvnn/AIAgentsStarterKit')

if os.environ.get('CHEAP_MODE') == 'True':
    cto_llm_name = os.environ.get('CHEAP_MODE_LLM')
    coder_llm_name = os.environ.get('CHEAP_MODE_LLM')
else:
    cto_llm_name = os.environ.get('CTO_AGENT_LLM')
    coder_llm_name = os.environ.get('CODER_AGENT_LLM')


def get_llm_client(model_name, temperature):
    # Its assumed that if you have an OPENROUTER_API_KEY you want to use OpenRouter.
    # Otherwise, you want to use OpenAI and OPENAI_API_KEY is required.
    if 'OPENROUTER_API_KEY' in os.environ:
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ['OPENROUTER_API_KEY'],
            temperature=temperature
        )
    else:
        return ChatOpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            temperature=temperature
        )

cto_llm = get_llm_client(
    model_name=os.environ.get('CTO_AGENT_LLM'),
    temperature=0.2
)
coder_llm = get_llm_client(
    model_name=os.environ.get('CODER_AGENT_LLM'),
    temperature=0.1
)


def get_github_info(repo_name = gh_repo_name):
    global gh_repo
    try:
        if not gh_repo:
            auth = Auth.Token(gh_access_token)
            gh = Github(auth=auth)
            gh_repo = gh.get_repo(repo_name)
        issues = gh_repo.get_issues(state='open')
        pulls = gh_repo.get_pulls(state='open')
        pulls_comments = gh_repo.get_pulls_comments()
        return issues, pulls, pulls_comments
    except Exception as e:
        print(f'[get_github_info] Errorg: {e}')
        raise e
        # return None

company_technology_preferences = '''
    We prefer to use a simple FastAPI backend that serves a React Native frontend with Mui.
    We like to host apps on a single AWS instance and uses Postgres as the database.
    We use git for version control and markdown for documentation.
    We use ffmpeg for video processing.
    All bash scripting should work on OSX and Ubuntu systems, the same way.
'''

agent_cto = Agent(
    role = "Chief Technology Officer (CTO)",
    llm = cto_llm,
    allow_delegation = False,
    verbose = True,
    goal = f"""
        As the CTO, your goal is to review the GitHub Issue for the App and create a high-level technical design document 
        that outlines the technologies, libraries, packages, and vendors to be used in the implementation.

        {company_technology_preferences}

        The design document should be clear, concise, and easy to follow. It should provide a technical roadmap for the 
        development team, considering the company's technology preferences and best practices. If there is confusing or 
        insufficient information in the Issue, you should ask for clarification.

        You should include the specific libraries, frameworks, and tools that should be used to implement the solution, 
        along with any necessary justifications or considerations. Provide guidance on the overall architecture and any 
        important design decisions.
    """,
    backstory = """
        You are an experienced Chief Technology Officer (CTO) with a strong background in software architecture and 
        engineering. You hold a Ph.D. in Computer Science from MIT and have a proven track record of making strategic 
        technology decisions that align with company goals and priorities.

        You have a deep understanding of modern web and mobile technologies, and you prefer to keep things simple and 
        efficient. You have standardized the company's technology stack to use React Native for the frontend, FastAPI 
        for the backend, and Postgres for the database. You also advocate for the use of git for version control, 
        markdown for documentation, ffmpeg for video processing, and bash scripting that works seamlessly on both 
        OSX and Ubuntu systems.

        Your role is to provide technical leadership and ensure that the development team has a clear direction and 
        the necessary resources to deliver high-quality software solutions.
    """,
)

agent_coder = Agent(
    role = "Technical Lead",
    llm = coder_llm,
    allow_delegation = True,
    verbose = True,
    goal = f"""
        As the Technical Lead, your goal is to review the CTO's technical design document and break it down into 
        actionable tasks for the development team. You will provide guidance and support to the coders throughout 
        the implementation process.

        {company_technology_preferences}

        You should ensure that the implementation follows the company's technology preferences and best practices. 
        Provide code snippets, examples, and explanations to help the coders understand the requirements and 
        implement the solution effectively.

        Coordinate with the CTO and the development team to address any technical challenges or roadblocks that arise 
        during the implementation process. Make sure that the final solution meets the requirements outlined in the 
        GitHub Issue and adheres to the technical design document.
    """,
    backstory = """
        You are an experienced Technical Lead with a strong background in software development and team management. 
        You have a Master's degree in Computer Science and have worked on numerous successful projects in your career.

        You have expertise in React Native, FastAPI, Postgres, git, bash, and ffmpeg. You are well-versed in the 
        company's technology stack and best practices, and you are committed to ensuring that the development team 
        delivers high-quality software solutions.

        Your role is to bridge the gap between the CTO's technical vision and the day-to-day implementation by the 
        development team. You provide technical guidance, code reviews, and mentorship to the coders, and you 
        work closely with the CTO to ensure that the project stays on track and meets its objectives.
    """,
)

cto_comment_flag = '[architect]'

def issue_needs_cto(issue):
    try:
        comments = issue.get_comments()
        
        message_history = []
        refactor_requested = False
        
        for comment in comments:
            if comment.body.lower().startswith('refactor'):
                message_history.append(Message('refactor_request', comment.body))
            elif comment.body.lower().startswith(cto_comment_flag):
                message_history.append(Message('cto_response', comment.body))
            else:
                message_history.append(Message('comment', comment.body))
        
        if message_history and message_history[-1].role == 'refactor_request':
            refactor_requested = True
        
        return refactor_requested, message_history
    except Exception as e:
        print(f'[issue_needs_cto] Error: {e}')
        import pdb; pdb.set_trace()
        return False, []

def create_cto_task(issue, message_history):
    '''
    Create a task for the architect to create a Technical Spec and Implementation Plan.
    `message_history` is a list of Message objects representing the comment history.
    '''
    try:
        print(f'create_cto_task: {issue}')
        
        history_str = '\n'.join(f'{msg.role.upper()}: {msg.content}' for msg in message_history)
        
        prompt = f'''
            {issue.body}
            
            Message History:
            {history_str}
        '''
        
        task = Task(
            description=f'''
                You are tasked with requirements gathering for the following Github Issue:
                {prompt}
                
                Return your questions and a high-level technical design document that outlines the technologies,
                libraries, packages, and vendors to be used in the implementation. The design document should be clear,
                concise, and easy to follow. It should provide a technical roadmap for the development team.
            ''',
            agent=agent_cto,
            expected_output='A Technical Spec and Implementation Plan for the following Github Issue',
            callback=lambda task: callback_cto_task(task, issue)
        )
        return task
    except Exception as e:
        print(f'[create_cto_task] Error: {e}')
        import pdb; pdb.set_trace()
        return None


def callback_cto_task(task_output, issue):
    try:
        print(f'callback_cto_task: {issue}')
        body = f'''{cto_comment_flag}\nc{task_output.raw_output}'''
        comment = issue.create_comment(
            body=body
        )
    except Exception as e:
        print(f'[callback_cto_task] Error: {e}')
        import pdb; pdb.set_trace()


def callback_coder_task(task_output, issue):
    base_ref = gh_repo.get_git_ref(f"heads/{gh_base_branch}")
    new_branch_name = f"refs/heads/feature/issue-{issue.id}"

    # Create a new branch from the base branch
    gh_repo.create_git_ref(
        ref=new_branch_name,
        sha=base_ref.object.sha
    )
    gh_repo.create_pull(
        base = gh_base_branch,
        head = new_branch_name,
        body = task_output.raw_output,
        issue = issue
    )


def callback_qa_task(task_output, issue):
    # TODO
    pass


def create_coder_task(issue, cto_spec):
    '''
    Create a task for the coder to implement the solution based on the CTO's technical spec and the existing codebase.
    '''
    try:
        print(f'create_coder_task: {issue}')

        task = Task(
            description=f'''
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
            ''',
            agent=agent_coder,
            expected_output='A pull request that implements the solution for the given GitHub issue',
            callback=lambda task: callback_coder_task(task, issue)
        )
        return task
    except Exception as e:
        print(f'[create_coder_task] Error: {e}')
        import pdb; pdb.set_trace()
        return None


def create_qa_task(issue, feedback):
    # TODO
    pass

def init_agents():
    cto_tasks = []
    coder_tasks = []

    issues, pulls, pulls_comments = get_github_info()

    for issue in issues:
        print(f'Issue: {issue}')
        if not issue.pull_request:
            refactor_requested, message_history = issue_needs_cto(issue)
            if refactor_requested:
                cto_tasks.append(create_cto_task(issue, message_history))
    
    crew = Crew(
        agents=[agent_cto, agent_coder],
        tasks=cto_tasks + coder_tasks,
        verbose=2,
        process=Process.sequential,  # Optional: Sequential task execution is default
        memory=True,
        cache=True,
        max_rpm=100,
        share_crew=True
    )

    print(f'cto_tasks={cto_tasks}')
    result = crew.kickoff()
    return result

result = init_agents()
