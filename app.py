from github import Github, Auth
import os

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()

gh_base_branch = os.environ.get('GH_BASE_BRANCH', 'main')
gh_access_token = os.environ.get('GH_ACCESS_TOKEN', '')
gh_repo_name = os.environ.get('GH_REPO_NAME', 'kvnn/AIAgentsStarterKit')


architect_llm = ChatOpenAI(model_name='gpt-4o', temperature=0.2)
developer_llm = ChatOpenAI(model_name='gpt-3-turbo', temperature=0.2)

gh_repo = None

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
        import pdb; pdb.set_trace()
        return None

app_description = '''
    The App is a FastAPI backend that serves a React Native frontend with Mui.
    The App is hosted on a single AWS instance and uses Postgres as the database.
    The App is improved via Github Issues and Pull Requests.
'''

agent_architect = Agent(
    role = "Software Architect",
    llm = architect_llm,
    allow_delegation = False,
    verbose = True,
    goal = """
        Consume an Issue for the App and create a design document that can be used by a developer to implement the solution.
        
        {app_description}
        The design document should be clear, concise, and easy to follow.
        It should describe in plain English how the app should be modified to fulfill the
        requirements of the Issue. If there is confusing or insufficient information in the Issue, you should ask for clarification.
        You should include the libraries, frameworks, and tools that should be used to implement the solution.
        You should provide sample code snippets where necessary.
    """,
    backstory = """
        You are an excellent software architect. 
        You are a MIT Computer Engineering graduate and love to keep things simple.
        You have landed on using React Native, FastAPI and Postgres for every project.
        You love git, bash, linux, ffmpeg and markdown.
    """,
)

agent_developer = Agent(
    role = "Staff Software Engineer",
    llm = developer_llm,
    allow_delegation = True,
    verbose = True,
    goal = f"""To provide succinct and state-of-the-art solution for The App. {app_description}.""",
    backstory = """
        You are a professional staff software engineer with 15 years of FAANG experience building high-quality
        web and mobile applications.
    """,
)

architect_spec_flag = '[architect spec]'

def issue_needs_architect(issue):
    try:
        comments = issue.get_comments()
        
        if not comments.totalCount:
            return True
        # A refactor request should include the previous completion
        # and the feedback given.
        elif comments.reversed[0].body.lower().startswith('refactor'):
            # TODO: the [1] here is brittle. We should get keep reversing until we find the previous completion via the architect_spec_flag
            return f'The feedback is: {comments.reversed[0].body} ; The previous implementation plan was {comments.reversed[1].body}'
        elif comments.reversed[0].body.lower().startswith(architect_spec_flag):
            return False

        # At this point we have an ambiguous comment thread, but we know that
        # the last comment was not a refactor or an architect spec.
        # If there is an architect spec in the thread, we should not create a new one.
        # Otherwise, we should.
        for comment in comments:
            if comment.body.lower().startswith(architect_spec_flag):
                return False
        return True
    except Exception as e:
        print(f'[issue_needs_architect] Error: {e}')
        import pdb; pdb.set_trace()
        return False


def callback_architect_task(task_output, issue):
    try:
        print(f'callback_architect_task: {issue}')
        body = f'''{architect_spec_flag}\nc{task_output.raw_output}'''
        comment = issue.create_comment(
            body=body
        )
    except Exception as e:
        print(f'[callback_architect_task] Error: {e}')
        import pdb; pdb.set_trace()


def callback_developer_task(task_output, issue):
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


def create_architect_task(issue, feedback):
    '''
    Create a task for the architect to create a Technical Spec and Implementation Plan.
    `feedback` is optional, and if provided, should be a string that will be appended to the task description.'''
    try:
        print(f'create_architect_task: {issue}')

        prompt = f'{issue.body} . A previous result was met with this feedback: {feedback}.' if isinstance(feedback, str) else issue.body

        task = Task(
            description=f'''
                You are tasked with creating an Implementation Plan for the following Github Issue:
                {prompt}''',
            agent = agent_architect,
            expected_output='A Technical Spec and Implementation Plan for the following Github Issue',
            callback = lambda task: callback_architect_task(task, issue)
        )
        return task
    except Exception as e:
        print(f'[create_architect_task] Error: {e}')
        import pdb; pdb.set_trace()
        return None


def init_agents():
    architect_tasks = []
    developer_tasks = []
    issues, pulls, pulls_comments = get_github_info()

    for issue in issues:
        print(f'Issue: {issue}')
        if not issue.pull_request:
            architect_feedback = issue_needs_architect(issue)
            if architect_feedback:
                architect_tasks.append(create_architect_task(issue, architect_feedback))
    
    crew = Crew(
        agents=[agent_architect, agent_developer],
        tasks=architect_tasks + developer_tasks,
        verbose=2,
        process=Process.sequential,  # Optional: Sequential task execution is default
        memory=True,
        cache=True,
        max_rpm=100,
        share_crew=True
    )

    print(f'architect_tasks={architect_tasks}')
    result = crew.kickoff()
    return result

result = init_agents()
