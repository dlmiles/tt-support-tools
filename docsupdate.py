#!/usr/bin/env python3
#
#	TinyTapeout project documentation update process.
#
#	This can be run by the source repo owner directly or
#	 could be run on behalf of the repo owner by a third party.
#
#	It has a --dry-run mode which will no perform any wiring modifications
#         to the outside world.
#
#	Options:
#		--source	"dlmiles/project-name" or
#				"https://github.com/dlmiles/project-name"
#		--ref		default: <blank> (assume HEAD of "main"
#		--target	default: "https://github.com/TinyTapeout/tinytapeout-06"
#		--dry-run	Do not push to a remote repo anything
#		--no-create-pr  Inhibit the creation of the PR at the end
#				(but this will create branch and push, possibly allowing
#				review on github in your own copy of the upstream repo
#				(tinytapeout-06) before then using the web based Github
#				option to Compare & Create Pull Request.
#
#	Example usage:
#		python3 -m venv venv
#		source venv/bin/activate
#		venv/bin/pip3 install -r requirements.txt
#		python3 docsupdate.py --log=DEBUG --source=dlmiles/project-name
#
#	The script needs a valid GH token (to push to a remote repo and create PR),
#	 this is the only modification action to create a PR against the target repo
#	(which anyone with a GH account can do)
#
#
#	Related Python API documentation links:
#		https://pygithub.readthedocs.io/en/stable/index.html
#		https://gitpython.readthedocs.io/en/stable/quickstart.html
#
#
#	Preprequisite tools:
#		apt-get install rsync diffstat
#
#
import os
import re
import sys
import json
import time
import click
import logging
import pathlib
import urllib3
import argparse
import datetime
import tempfile
import textwrap
import subprocess

import PyInquirer

from collections import OrderedDict

# PyGithub
from github import Github, enable_console_debug_logging
from github import Auth
# GitPython
from git import Repo


#API_BASE_URL = "hostname/api/v3" # Github enterprise
API_BASE_URL = "api.github.com"


def resolve_access_token() -> str:
    for key in ['GH_TOKEN', 'GITHUB_TOKEN']:
        if key in os.environ:
            token = os.environ[key]
            if len(token) > 0:
                logging.info(f"Token found in ${key}")
                return token

    # apt-get install gh  # as in https://cli.github.com/
    # export GH_TOKEN=$(gh auth token)
    print(f"Unable to resolve github access_token from enviroment \$GH_TOKEN or \$GITHUB_TOKEN", file=sys.stderr)
    return None


def resolve_username(g) -> str:
    if g:
        res = g.get_user()
        if res and len(res.login) > 0:
            print(f"username={res.login}")
            return res.login

    for key in ['GITHUB_ACTOR', 'USERNAME']:
        if key in os.environ:
            username = os.environ[key]
            if len(username) > 0:
                return username
    return None


def setup() -> Github:
    # using an access token
    token = resolve_access_token()
    if token is None:
        return None

    auth = Auth.Token(token)

    g = Github(auth=auth)
    g = Github(base_url=f"https://{API_BASE_URL}", auth=auth)

    return g


def cleanup(g: Github) -> None:
    # To close connections after use
    g.close()


def find_project_metadata(target_repo_dir: str, source_repo: str) -> dict:
    # Validate sane input
    assert len(target_repo_dir) > 0
    assert len(source_repo) > 0

    projects_dir = pathlib.Path(target_repo_dir, 'projects')
    if not projects_dir.is_dir():
        return None

    for single_project_dir in projects_dir.iterdir():
        commit_id_json = pathlib.Path(single_project_dir, 'commit_id.json')
        if not commit_id_json.is_file():
            continue

        logger.info(f"Examine... {commit_id_json}")
        with open(commit_id_json) as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
            
            # Find project entry
            if source_repo == data['repo']:
                logger.info(f"Found... {commit_id_json}")
                return data

    return None
    

def source_repo():
    
    
    # Setup new branch
    # Apply documentation update over the top

    # Produce commit summary text
    #  When who what
    #  diffstat ?

    # Create commit (on tinytapeout-xx checkout)
    
    # if not dryrun:
    # Check access to tinytapeout-xx to commit new branch "docs-prj123-20220422"
    # Otherwise commit to origin repo

    # Dump git command action
    # Dump commit to console

    # Push commit (to repo)
    
    # Cleanup $TMPDIR
    pass    


def create_pr(pr_repo: str):
    repo = g.get_repo("PyGithub/PyGithub")

    title = f"Project Docs Update: {project} {project_gh_repo}"

    body = '''

SUMMARY

Project Docs Update: {project} {project_gh_repo}

Source repo:

Source git logs / name / history / timestamp

'''

    pr = repo.create_pull(base="master", head="develop", title=title, body=body)
    
    print(f"pr.number")
    #PullRequest(title="Use 'requests' instead of 'httplib'", number=664)


# when: int | datetime.datetime
def datetime_yyyymmdd(when) -> str:
    if type(when) is int:
        when = datetime.datetime.fromtimestamp(when)	# epoch-seconds
    elif type(when) is not datetime.datetime:
        assert False, f"Unexpected type: {type(when)}"
    return when.strftime('%Y%m%d')


# "" -> "docs-20240501-"
def build_branch_name(repo: str) -> str:
    yyyymmdd = datetime_yyyymmdd(datetime.datetime.now())
    exten = re.sub(r'^.*/', '', repo) # sanitize
    exten = re.sub(r'[\W_]+', '', exten)
    return f"docs-{yyyymmdd}-{exten}"


def build_repo_url(repo) -> None:
    if repo == 'dlmiles/tinytapeout-06':
        return f"/home/dlm/git/projects_tt03/tinytapeout-06"
    return f"https://github.com/{repo}"


def g_cooked_create_a_fork() -> bool:
    # curl -L  -X POST \
    #  -H "Accept: application/vnd.github+json" \
    #  -H "Authorization: Bearer <YOUR-TOKEN>" \
    #  -H "X-GitHub-Api-Version: 2022-11-28" \
    #  https://api.github.com/repos/OWNER/REPO/forks \
    #  -d '{"organization":"octocat","name":"Hello-World","default_branch_only":true}'
    g.create_fork(organisation = None, name = name, default_branch_only = true)


# If we can access the API: //api.github.com/repos/{user}/{repo}/collaborators
# When we have push access to the repo this API will not error, so this is a non-destructive
# test for push access based on the TOKEN we currently have.
def gh_cooked_collaborators(g, repo: Repository)-> bool:
    has_push_access = False
    try:
        res = repo.get_collaborators()
        if res:
            for i in res:
                # We need to both access the API and then access the enumeration PaginationList
                # if one or more entries exist, it worked, so we must have push repo access.
                print(f"i={i}")
                has_push_access = True
                break
    except GithubException as e:
        # Just assume no access
        print(f"gh_cooked_collaborators(repo={repo}) = {e}")
    return has_push_access


def do_test():
    # Prepare to use Github APIs
    g = setup()
    if g is None:
        sys.exit(1)

    username = resolve_username(g)


    # Check which repo has write access for pushing the branch

    # curl -u your_username:your_personal_access_token \
    # -H "Accept: application/vnd.github.v3+json" \
    # https://api.github.com/repos/octocat/hello-world/collaborators/USERNAME/permission
    # //api.github.com/repos/dlmiles/tinytapeout-06/collaborators
    gh_final_repo = 'TinyTapeout/tinytapeout-06'
    g_final_repo = g.get_repo(gh_final_repo)
    if g_final_repo is None:
        printf(f"gh_final_repo={gh_final_repo} does not exist")
        sys.exit(1)
    g_final_repo_has_push_access = gh_cooked_collaborators(g, g_final_repo)
    print(f"g_final_repo_has_push_access={g_final_repo_has_push_access}")

    print(f"gh_source_repo={gh_source_repo}")
    g_source_repo = g.get_repo(gh_source_repo)
    if g_source_repo is None:
        printf(f"gh_source_repo={gh_source_repo} does not exist")
        sys.exit(1)
    g_source_repo_has_push_access = gh_cooked_collaborators(g, g_source_repo)
    print(f"g_source_repo_has_push_access={g_source_repo_has_push_access}")

    print(f"gh_target_repo={gh_target_repo}")
    g_target_repo = g.get_repo(gh_target_repo)
    if g_target_repo is None:
        print(f"gh_target_repo={gh_target_repo} does not exist")
        sys.exit(1)
    g_target_repo_has_push_access = gh_cooked_collaborators(g, g_target_repo)
    print(f"g_target_repo_has_push_access={g_target_repo_has_push_access}")
    


if __name__ == '__main__':
    if not 'CI' in os.environ:
        enable_console_debug_logging() # This maybe a bad idea to enable in CI (token looks removed at least)

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--ref', required=False)
    parser.add_argument('--target', required=True, default=['TinyTapeout/tinytapeout-06'])
    parser.add_argument('--push-repo')	# source or target
    parser.add_argument('--dry-run')  # do not modify any external repo
    parser.add_argument('--no-create-pr')
    parser.add_argument('--verbose')
    parser.add_argument('--interactive')

    logger = logging.getLogger(__name__)
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)


    do_test()

    # Detect my GH username # https://api.github.com/user # used as a default to resolve
    # FIXME

    # Sanity check argument
    print(f"main")
    gh_target_repo = 'dlmiles/tinytapeout-06'
    gh_target_ref = 'main'

    # Accepts forms:
    #   dlmiles/tt06-muldiv8
    #   https://github.com/dlmiles/tt06-muldiv8
    gh_source_repo = 'dlmiles/tt06-muldiv8'
    gh_source_repo = gh_source_repo.removeprefix('https://github.com/')
    # Validate, does not contain ':' and has exactly one '/'
    if gh_source_repo.count(':') > 0 or gh_source_repo.count('/') != 1:
        print(f"source={gh_source_repo}")
        print(f"The option --source does not look a valid repository such as: https://github.com/octocat/project", file=sys.stderr)
        sys.exit(1)

    gh_source_ref = ''
    if len(gh_source_ref) == 0:
        gh_source_ref = 'main'

    # checkout_to_tmpdir (source)
    #
    tempdir = tempfile.TemporaryDirectory()
    logging.debug(f'Tempdir = {tempdir.name}')
    tempdirname = f"{tempdir.name}1"
    os.rename(tempdir.name, tempdirname)
    # git clone --no-checkout --depth=1 --no-tags https://github.com/TinyTapeout/tinytapeout-06

    if True:
        source_local_dir = pathlib.Path(tempdirname, 'source_repo')
        gh_source_repo_url = build_repo_url(gh_source_repo)
        logging.debug(f"source_local_dir={source_local_dir} {gh_source_repo_url}")
        # Need all history to validate original commit-id against repo
        source_repo = Repo.clone_from(gh_source_repo_url, source_local_dir, branch=gh_source_ref)
        source_hash = source_repo.head.commit.tree
        logging.debug(f"source_hash={source_hash}")

        target_local_dir = pathlib.Path(tempdirname, 'target_repo')
        logging.debug(f"target_local_dir={target_local_dir}")
        target_repo = Repo.clone_from(build_repo_url(gh_target_repo), target_local_dir, depth=1, no_tags=True, single_branch=True, branch=gh_target_ref)
        target_hash = target_repo.head.commit.tree
        logging.debug(f"target_hash={target_hash}")

        # Validate repo exists in shuttle
        metadata = find_project_metadata(str(target_local_dir.absolute()), gh_source_repo_url)
        if metadata is None:
            print(f"Project {gh_source_repo_url} not found in target repo {gh_target_repo}", file=sys.stderr)
            sys.exit(1)
        logging.debug(f"Found project metadata={metadata}")

        # Validate original commit ID (as used in shuttle checkout, exists)
        # This is a sanity to check to make sure we are looking at the correct origin repo
        # Validate the original commit-id used in the shuttle is present in the source_repo
        items = source_repo.iter_commits(rev=metadata['commit'], max_count=1)
        if len(list(items)) == 0:
            print(f"Project {gh_source_repo_url} not commit log entry for {metadata['commit']} found, aborting", file=sys.stderr)
            sys.exit(1)

            # Validate the new documentation commit ID (the one to pickup the docs from, allow all refs,
        #  use standard git ref resolution methods to resolve into commit-id hash)
        # Validate this commit ID exists (probably the clone would have failed above but...)
        items = source_repo.iter_commits(rev=gh_source_ref, max_count=1)
        if len(list(items)) == 0:
            print(f"Project {gh_source_repo_url} no commit log entry for request ref {gh_source_ref}, aborting", file=sys.stderr)
            sys.exit(1)

    project_name_top_module = 'tt_um_dlmiles_muldiv8'
    # Maybe better to generate a filelist by processing info.md to provide include argument

    gh_source_repo_url = build_repo_url(gh_source_repo) # DEBUG remove
    if source_local_dir is None:	# DEBUG remove
        source_local_dir = '/tmp/foo1234/source'
    if target_local_dir is None:
        target_local_dir = '/tmp/foo1234/target'

    # DEBUG edit
    cmd = [ f"echo FOO >> {source_local_dir}/docs/info.md" ]
    res_edit = subprocess.run(cmd, timeout=30, shell=True)
    logger.debug(res_edit)

    # This controls what files are picked up and overlayed, prefer to use 'rsync'
    #  as you can more or less control every aspect of how that is performed.
    # TODO better to process the info.md and produce a list of asset files and
    #  turn into --include arguments here.
    cmd = [ 'rsync', '-rcIO', f"{source_local_dir}/docs/", f"{target_local_dir}/projects/{project_name_top_module}/docs/", '--include', "info.md", '--include', "*.png" ]
    print(' '.join(cmd))
    #cmd = [ 'sleep', '3' ] # DEBUG
    #print(f"Ctrl-Z or Ctrl-C wait... 10")
    #time.sleep(10)
    res_rsync = subprocess.run(cmd, timeout=30)
    logger.debug(res_rsync)
    logger.debug(f"subprocess[rsync] rc={res_rsync.returncode}")

    scommit = source_repo.head.commit
    source_commit_hash   = scommit.hexsha
    source_commit_hash8  = source_commit_hash[0:7]
    source_commit_author = scommit.author
    source_commit_date   = datetime_yyyymmdd(scommit.authored_date)



    git_status = target_repo.index.diff(None) # git status
    git_status_count = len(git_status)
    if git_status_count == 0:	# clean
        print(f"No changes found to merge from {gh_source_repo_url}~{source_commit_hash}#{source_commit_date}")
        sys.exit(0)

    print(f"{git_status_count} Change(s) found to merge from {gh_source_repo_url}~{source_commit_hash}#{source_commit_date}")
    
    hcommit = source_repo.head.commit
    diff = hcommit.diff()
    # diffstat {project_name_top_module}
    res_diffstat = subprocess.run([f"cd {target_local_dir} && git diff -- \"projects/{project_name_top_module}\" | diffstat -w73"], shell=True, timeout=30, capture_output=True)
    print(res_diffstat)
    diffstat = res_diffstat.stdout.decode('ascii').replace('\n', "\n    ")

    # Generate commit messages
    commit_message = textwrap.dedent(f'''
    Docs: {project_name_top_module} {source_commit_hash8}~{source_commit_date}
    
    Source Repo: {gh_source_repo_url}
                 {source_commit_hash}
                 {source_commit_date}
                 
    {diffstat}
                 
    Automated Commit tt-support-tools/docsupdate.py
    ''')
    print(f"Commit Message =\n{commit_message}")

    # Create branch "docs-YYYYMMDD-tt_um_xxxxxxxxx"
    new_branch_name = build_branch_name(gh_source_repo_url)
    logging.debug(f"new_branch_name={new_branch_name}")
    target_repo_branch = target_repo.create_head(new_branch_name, 'HEAD')

    # Generate commit (locally commit)
    ncommit = target_repo.index.commit(commit_message)    
    logging.debug(f"{ncommit}")

    # Prepare to use Github APIs
    g = setup()
    if g is None:
        sys.exit(1)

    username = resolve_username(g)


    # Check which repo has write access for pushing the branch

    # curl -u your_username:your_personal_access_token \
    # -H "Accept: application/vnd.github.v3+json" \
    # https://api.github.com/repos/octocat/hello-world/collaborators/USERNAME/permission
    # //api.github.com/repos/dlmiles/tinytapeout-06/collaborators
    gh_final_repo = 'TinyTapeout/tinytapeout-06'
    g_final_repo = g.get_repo(gh_final_repo)
    if g_final_repo is None:
        printf(f"gh_final_repo={gh_final_repo} does not exist")
        sys.exit(1)
    #g_final_repo_has_push_access = gh_cooked_collaborators(g_final_repo)
    g_final_repo_has_push_access = False
    try:
        res = g_final_repo.get_collaborators()
        if res:
            for i in res:
                print(f"i={i}")
                g_final_repo_has_push_access = True
    except GithubException as e:
        # Just assume no access
        print(f"{e}")
    print(f"g_final_repo_has_push_access={g_final_repo_has_push_access}")

    print(f"gh_source_repo={gh_source_repo}")
    g_source_repo = g.get_repo(gh_source_repo)
    res = g_source_repo.get_collaborators()
    if res:
        for i in res:
            print(f"i={i}")

    print(f"gh_target_repo={gh_target_repo}")
    g_target_repo = g.get_repo(gh_target_repo)
    res = g_target_repo.get_collaborators()
    if res:
        for i in res:
            print(f"i={i}")

    # If no push access to gh_final_repo, then need to at least have a fork
    # Check dry-run state
    # Offer to create fork ?
    # Make user run this script interactively (to offer to create fork)


    push_repo = target_repo

    # Provide command line option
    # Push (or dry-run)
    # FIXME how to specify which remote
    push_info = push_repo.push(f"{ncommit}:{new_branch_name}")

    # Open PR (always against target_repo)
    


    logging.debug(f'Cleanup Tempdir = {tempdir.name}')
    logging.debug(f'Cleanup Tempdir = {tempdirname}')
    #time.sleep(10)	# debugging (enable line and use Ctrl-Z)
    tempdir.cleanup()

    cleanup(g)

    sys.exit(0)
