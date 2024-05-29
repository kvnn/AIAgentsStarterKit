from github import Github, Auth
import os

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv


load_dotenv()

gh_base_branch = os.environ.get('GH_BASE_BRANCH', 'main')
gh_access_token = os.environ.get('GH_ACCESS_TOKEN', '')
gh_repo_name = os.environ.get('GH_REPO_NAME', 'kvnn/AIAgentsStarterKit')
architect_model_name = 'gpt-3-turbo'
developer_model_name = 'gpt-3-turbo'

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


agent_architect = Agent(
    role = "Software Architect",
    goal = """
        Take a Github Issue and create a Github Pull Request with 
        a technical spec and implementation plan for an automated coding agents that is powered by an LLM.
        Since an LLM will be following this plan, be direct and clear in your instructions.
        The developer agents are good at writing code, but not at making system design decisions.
        Do not mention timelines or deadlines in the spec, but do provide a clear and concise plan.
        All code will be written in Python. 
        Do not overcomplicate the plan, but do provide a clear and concise plan.
        For example, if the issue calls for something as simple as "add the `reference_id` column to the get-users sql query",
        your technical spec should be very succinct.
    """,
    backstory = """
        You are an excellent software architect. 
        You are a MIT Computer Engineering graduate and love to keep things simple.
        You have landed on using React Native, FastAPI and Postgres for every project.
        We keep all of our infrastructure on AWS and can run multiple FastAPI projects
        on a single EC2 instance with a very simple pattern that you articulated (separate git repositories corresponding to systemd services and distinct ports).

        You love git, bash, linux, ffmpeg and markdown.
    """,
    allow_delegation = False,
    verbose = True,
    # llm = architect_model_name
)

agent_developer = Agent(
    role = "Staff Software Engineer",
    goal = """Primary goal is to work on a Pull Request To keep the Software Architect happy, to have as few pull-request review items reported as possible before
    your code is merged, to provide succinct and state-of-the-art solutions using high quality, simple React, Python and CSS.""",
    backstory = """
        You have been a staff software engineer for 4 months, and are *extremely* keen on keeping your job.
        You are intimidated by the Software Architect - he's a bit cantankerous and much smarter than you.
        But he is fair, and as long as you put full effort into your coding and your double-checks
        (you should always check your work), then the pull requests go pretty smooth.
    """,
    # llm = developer_model_name
)

architect_spec_flag = '[architect spec]'

def issue_needs_architect(issue):
    try:
        comments = issue.get_comments()
        
        if not comments.totalCount:
            return True
        elif comments.reversed[0].body.lower().startswith('refactor'):
            return True
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


def create_architect_task(issue):
    try:
        print(f'create_architect_task: {issue}')
        task = Task(
            description=f'''
                You are tasked with creating a Technical Spec and Implementation Plan for the following Github Issue:
                {issue.body}''',
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

        if not issue.pull_request and issue_needs_architect(issue):
            architect_tasks.append(create_architect_task(issue))
    
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
import pdb; pdb.set_trace()