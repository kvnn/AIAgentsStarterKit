import base64
from collections import namedtuple
import os
from time import sleep, time
import random

from github import Github, Auth
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from interpreter import interpreter

from agents import (
    agent_instructor,
    agent_coder,
    get_planner_task_description,
    planner_task_expected_output,
    # get_planner_refactor_task_description,
    get_coder_task_description,
    get_coder_refactor_task_description,
)


load_dotenv()

Message = namedtuple('Message', ['role', 'content'])
bot_flag_planner = '[coding agent]'
gh_base_branch = os.environ.get('GH_BASE_BRANCH', 'main')
gh_access_token = os.environ.get('GH_ACCESS_TOKEN', '')
gh_repo_name = os.environ.get('GH_REPO_NAME', 'kvnn/AIAgentsStarterKit')
gh_repo = None

def get_github_info(repo_name=gh_repo_name):
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
        print(f'[get_github_info] Error: {e}')
        raise e


def issue_needs_planner(issue):
    try:
        comments = issue.get_comments()
        
        message_history = []
        refactor_requested = False
        
        for comment in comments:
            if comment.body.lower().startswith('refactor'):
                message_history.append(Message('refactor_request', comment.body))
            elif comment.body.lower().startswith(bot_flag_planner):
                message_history.append(Message('planner_response', comment.body))
            else:
                message_history.append(Message('comment', comment.body))
        
        if message_history and message_history[-1].role == 'refactor_request':
            refactor_requested = True
        
        return refactor_requested, message_history
    except Exception as e:
        print(f'[issue_needs_planner] Error: {e}')
        raise e


def issue_approved_by_human(issue):
    try:
        comments = issue.get_comments()
        if comments.totalCount == 0:
            return False
        
        last_comment = comments.reversed[0].body.lower()
        return last_comment.startswith('approve')
    except Exception as e:
        print(f'[issue_approved_by_human] Error: {e}')
        raise e


def pull_request_needs_refactoring(pull_request):
    try:
        comments = pull_request.get_comments()
        if comments.totalCount == 0:
            return False
        
        last_comment = comments.reversed[0].body.lower()
        return last_comment.startswith('refactor')
    except Exception as e:
        print(f'[pull_request_needs_refactoring] Error: {e}')
        raise e


def create_coder_refactor_task(pull_request):
    try:
        print(f'create_coder_refactor_task: {pull_request}')
        
        issue = pull_request.base.repo.get_issue(pull_request.number)
        plan = get_plan_from_issue(issue)
        
        refactor_comments = []
        comments = pull_request.get_issue_comments()
        for comment in comments:
            if comment.body.lower().startswith('refactor'):
                refactor_comments.append(comment.body)
        
        refactor_feedback = '\n'.join(refactor_comments)
        
        task = Task(
            description=get_coder_refactor_task_description(pull_request, plan, refactor_feedback),
            agent=agent_coder,
            expected_output='Updated pull request with refactored code',
            callback=lambda task: callback_coder_refactor_task(task, pull_request)
        )
        return task
    except Exception as e:
        print(f'[create_coder_refactor_task] Error: {e}')
        raise e


def create_planner_task(issue, message_history):
    '''
    Create a task for the architect to create a Technical Spec and Implementation Plan.
    `message_history` is a list of Message objects representing the comment history.
    '''
    try:
        print(f'create_planner_task: {issue}')
        
        history_str = '\n'.join(f'{msg.role.upper()}: {msg.content}' for msg in message_history)
        
        prompt = f'''
            {issue.title}
            {issue.body}
            
            Message History:
            {history_str}
        '''
        
        task = Task(
            description=get_planner_task_description(prompt),
            agent=agent_instructor,
            expected_output=planner_task_expected_output,
            callback=lambda task: callback_planner_task(task, issue)
        )
        return task
    except Exception as e:
        print(f'[create_planner_task] Error: {e}')
        raise e


def callback_planner_task(task_output, issue):
    try:
        print(f'callback_planner_task: {issue}')
        body = f'''{bot_flag_planner}\n{task_output.raw_output}'''
        comment = issue.create_comment(
            body=body
        )
    except Exception as e:
        print(f'[callback_planner_task] Error: {e}')
        raise e


def callback_coder_task(task_output, issue):
    base_ref = gh_repo.get_git_ref(f"heads/{gh_base_branch}")
    new_branch_name = f"refs/heads/feature/issue-{issue.id}"

    # Create a new branch from the base branch
    gh_repo.create_git_ref(
        ref=new_branch_name,
        sha=base_ref.object.sha
    )
    gh_repo.create_pull(
        base=gh_base_branch,
        head=new_branch_name,
        body=task_output.raw_output,
        issue=issue
    )

def callback_coder_refactor_task(task_output, pull_request):
    try:
        # Extract the refactored code from the task output
        refactored_code = extract_code_changes(task_output.raw_output)
        
        # Get the existing pull request file
        contents = pull_request.get_files()
        if contents.totalCount != 1:
            raise ValueError(f"Expected 1 file in the pull request, but found {contents.totalCount}")
        
        file_content = contents[0]
        file_path = file_content.filename
        file_sha = file_content.sha
        
        # Update the file with the refactored code
        commit_message = f"Refactored code for pull request #{pull_request.number}"
        content = base64.b64encode(refactored_code.encode("utf-8")).decode("utf-8")
        update_result = pull_request.base.repo.update_file(
            path=file_path,
            message=commit_message,
            content=content,
            sha=file_sha,
            branch=pull_request.head.ref
        )
        
        # Add a comment to the pull request with the refactoring details
        comment_body = f"Refactored code based on the provided feedback:\n\n{task_output.raw_output}"
        pull_request.create_issue_comment(comment_body)
        
        print(f"Updated pull request: {pull_request.html_url}")
    except Exception as e:
        print(f"[callback_coder_refactor_task] Error: {e}")
        raise e

def callback_qa_task(task_output, issue):
    # TODO
    pass


def create_coder_task(issue, plan):
    '''
    Create a task for the coder to implement the solution based on the Planner's plan
    '''
    try:
        print(f'create_coder_task: {issue}')

        task = Task(
            description=get_coder_task_description(issue, plan),
            agent=agent_coder,
            expected_output='A pull request that implements the solution for the given GitHub issue',
            callback=lambda task: callback_coder_task(task, issue)
        )
        return task
    except Exception as e:
        print(f'[create_coder_task] Error: {e}')
        raise e


def create_qa_task(issue, feedback):
    # TODO
    pass

def get_plan_from_issue(issue):
    try:
        comments = issue.get_comments()
        
        for comment in comments.reversed:
            if comment.body.lower().startswith(bot_flag_planner):
                return comment.body
        
        return None
    except Exception as e:
        print(f'[get_plan_from_issue] Error: {e}')
        raise e

def planner_has_commented(issue):
    comments = issue.get_comments()

    for comment in comments:
        if bot_flag_planner in comment.body.lower():
            return True

    return False


def is_pull_request_open(issue):
    if not issue.pull_request:
        return False
    
    pull_request_url = issue.pull_request.html_url
    pull_number = int(pull_request_url.split('/')[-1])
    pull_request = gh_repo.get_pull(pull_number)
    
    return pull_request.state == 'open'


def create_pull_request_from_plan(issue, plan):
    global gh_repo

    try:
        # Extract necessary information from the plan
        title = issue.title
        description = f'''Automated PR for Issue #{issue.number}
        Plan: {plan}
        '''
        new_branch_name = f'feature/issue-{issue.number}-{issue.id}-{random.randint(1000, 9999)}'

        # Verify the base branch exists
        base_branch = gh_base_branch
        try:
            base_branch_commit = gh_repo.get_branch(base_branch).commit.sha
        except Exception as e:
            print(f'Error: Base branch "{base_branch}" not found: {e}')
            return None

        # Create a new branch for the pull request
        gh_repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=base_branch_commit)

        # Create a new file with the plan content in the new branch
        gh_repo.create_file(
            path=f"plan_{issue.id}.md",
            message=f"Create plan for {title}",
            content=description,
            branch=new_branch_name,
        )

        # Create a new pull request
        pull_request = gh_repo.create_pull(
            issue=issue,
            body=description,
            head=new_branch_name,
            base=base_branch
        )

        return pull_request
    except Exception as e:
        print(f'[create_pull_request_from_plan] Error: {e}')
        raise e


def start_agent_loop():
    loop_index = 0
    total_duration = 0

    while True:
        try:
            print(f'[start_agent_loop] Starting loop {loop_index}...')
            start_time = time()

            issue_tasks = []
            coder_tasks = []

            issues, pulls, pulls_comments = get_github_info()

            for issue in issues:
                print(f'Issue: {issue}')
                if not is_pull_request_open(issue):
                    refactor_requested, message_history = issue_needs_planner(issue)
                    if refactor_requested or not planner_has_commented(issue):
                        issue_tasks.append(
                            create_planner_task(issue, message_history)
                        )
                    elif issue_approved_by_human(issue):
                        plan = get_plan_from_issue(issue)
                        create_pull_request_from_plan(issue, plan)
                        # coder_tasks.append(create_coder_task(issue, plan))

            # Iterate over open pull requests to check if refactoring is needed
            for pull_request in pulls:
                if pull_request_needs_refactoring(pull_request):
                    coder_tasks.append(create_coder_refactor_task(pull_request))

            tasks = issue_tasks + coder_tasks
            
            num_human_tasks = (
                len([issue for issue in issues if not issue.pull_request and not issue_needs_planner(issue)[0]]) +
                len([pull for pull in pulls if not pull_request_needs_refactoring(pull)])
            )

            print(f'- Human task count: {num_human_tasks}')
            print(f'- Planner task count: {len(issue_tasks)}')
            print(f'- Coder task count: {len(coder_tasks)}')

            if tasks:
                crew = Crew(
                    agents=[agent_coder],
                    tasks=tasks,
                    verbose=2,
                    process=Process.sequential,
                    memory=True,
                    cache=True,
                    max_rpm=100,
                    share_crew=True
                )
                
                result = crew.kickoff()
            
            loop_index += 1
            total_duration += time() - start_time

            # print(f'[start_agent_loop] result info: {result}')
        except Exception as e:
            print(f"[start_agent_loop] Error: {e}")
            raise e

        sleep(5)

if __name__ == "__main__":
    start_agent_loop()
