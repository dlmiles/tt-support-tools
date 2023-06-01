import base64
from urllib.parse import urlparse
import logging
import requests
import os
import zipfile
import io
import errno
import time
import sys


def unique(duplist):
    unique_list = []
    # traverse for all elements
    for x in duplist:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    return unique_list


def fetch_file(url, filename):
    logging.info("trying to download {}".format(url))
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning("couldn't download {}".format(url))
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)

    with open(filename, 'wb') as fh:
        logging.info("written to {}".format(filename))
        fh.write(r.content)


def check_status(r):
    if r.status_code == 401:
        logging.error("unauthorised, check INFO.md for information about GitHub API keys")
        exit(1)

def check_rate_limit(r):
    remaining = int(r.headers.get('X-RateLimit-Remaining', -1))
    limit = int(r.headers.get('X-RateLimit-Limit', -1))
    reset = int(r.headers.get('X-RateLimit-Reset', sys.maxsize))

    s = ''
    status_code = r.status_code
    content_type = r.headers.get('content-type', '')
    if content_type != '':
        s += f" with {content_type}"
    content_length = r.headers.get('content-length', -1)
    if content_length >= 0:
        s += f" {content_length} byte(s)"

    when = int(reset - time.time())
    if when < 0:
        when = 0
    if remaining < (limit * 0.50):
        logging.info(f"HTTP/{status_code} X-RateLimit {remaining}/{limit} resets in {when}s [{reset}] {s}")

    # Only throttle within limits
    if remaining > 0 and remaining < 100 and when > 0:
        delay = (when / remaining) + 1
        # 1000 in 20min maybe the default seen
        if delay > 0 and delay < 10:
            logging.warning("X-RateLimit client throttle delay %d" % delay)
            time.sleep(delay)

    if remaining == 0:
        logging.error("X-RateLimit no API requests remaining")
        exit(1)

    #logging.debug("X-RateLimit API requests remaining %d" % remaining)


def headers_try_to_add_authorization_from_environment(headers: dict) -> bool:
    gh_token = os.getenv('GH_TOKEN', '')                 # override like gh CLI
    if not gh_token:
        gh_token = os.getenv('GITHUB_TOKEN', '')         # GHA inherited

    if len(gh_token) > 0:
        # As per https://docs.github.com/en/rest/overview/authenticating-to-the-rest-api
        headers['authorization'] = 'Bearer ' + gh_token
        return True

    # Use a token instead which is designed to limit exposure of passwords
    # I can't find any GH docs explaining use cases for Basic auth and confirming a token
    # can be used instead of PASSWORD in the password field of authorization header.
    gh_username = os.getenv('GH_USERNAME', '')           # override like gh CLI
    if not gh_username:
        gh_username = os.getenv('GITHUB_ACTOR', '')      # GHA inherited

    gh_password = os.getenv('GH_PASSWORD', '')

    if len(gh_username) > 0 and len(gh_password) > 0:
        auth_string = gh_username + ':' + gh_password
        encoded = base64.b64encode(auth_string.encode('ascii'))
        headers['authorization'] = 'Basic ' + encoded.decode('ascii')
        return True

    print("WARNING: No github token found from environment, trying public API requests without, see docs/INFO.md#instructions-to-build-gds", file=sys.stderr)
    return False

def fetch_file_from_git(git_url, path):
    # get the basics
    user_name, repo = split_git_url(git_url)

    headers = {
        "Accept"        : "application/vnd.github+json",
        }
    # authenticate for rate limiting
    headers_try_to_add_authorization_from_environment(headers)

    api_url = 'https://api.github.com/repos/%s/%s/contents/%s' % (user_name, repo, path)

    logging.debug(api_url)
    r = requests.get(api_url, headers=headers)
    check_status(r)
    check_rate_limit(r)

    data = r.json()
    if 'content' not in data:
        return None

    file_content = data['content']

    file_content_encoding = data.get('encoding')
    if file_content_encoding == 'base64':
        file_content = base64.b64decode(file_content)

    return file_content


# the latest artifact isn't necessarily the one related to the latest commit, as github
# could have taken longer to process an older commit than a newer one.
# so iterate through commits and return the artifact that matches
def get_most_recent_action_url(commits, artifacts):
    release_sha_to_download_url = {artifact['workflow_run']['head_sha']: artifact['archive_download_url'] for artifact in artifacts}
    for commit in commits:
        if commit['sha'] in release_sha_to_download_url:
            return release_sha_to_download_url[commit['sha']]


def get_most_recent_action_page(commits, runs):
    release_sha_to_page_url = {run['head_sha']: run['html_url'] for run in runs if run['name'] == 'gds'}
    for commit in commits:
        if commit['sha'] in release_sha_to_page_url:
            return release_sha_to_page_url[commit['sha']]


def split_git_url(url):
    res = urlparse(url)
    try:
        _, user_name, repo = res.path.split('/')
    except ValueError:
        logging.error(f"couldn't split repo from {url}")
        exit(1)
    repo = repo.replace('.git', '')
    return user_name, repo


# download the artifact for each project to get the gds & lef
def install_artifacts(url, directory):
    logging.debug(url)
    user_name, repo = split_git_url(url)

    headers = {
        "Accept"        : "application/vnd.github+json",
        }
    # authenticate for rate limiting
    headers_try_to_add_authorization_from_environment(headers)

    # first fetch the git commit history
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/commits'
    r = requests.get(api_url, headers=headers)
    check_status(r)
    check_rate_limit(r)

    commits = r.json()

    # now get the artifacts
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/actions/artifacts'
    r = requests.get(api_url, headers=headers, params={'per_page': 100})
    check_status(r)
    data = r.json()

    # check there are some artifacts
    if 'artifacts' not in data:
        logging.error(f"no artifact found for {url}")
        exit(1)
    else:
        # only get artifacts called GDS
        artifacts = [a for a in data['artifacts'] if a['name'] == 'GDS']
        logging.debug(f"found {len(artifacts)} artifacts")

    if len(artifacts) == 0:
        logging.error("no artifacts for this project")
        exit(1)

    download_url = get_most_recent_action_url(commits, artifacts)

    # need actions access on the token to get the artifact
    # won't work on a pull request because they won't have the token
    attempts = 1
    max_attempts = 3
    while attempts < max_attempts:
        try:
            logging.debug(f"download url {download_url} attempt {attempts}")
            r = requests.get(download_url, headers=headers)
            check_status(r)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(directory)
            break
        except zipfile.BadZipFile:
            attempts += 1
            logging.warning(f"problem with zipfile, retry {attempts}")

    if attempts == max_attempts:
        logging.error("gave up downloading zipfile")
        exit(1)


def get_latest_action_url(url, directory):
    logging.debug(url)
    user_name, repo = split_git_url(url)

    headers = {
        "Accept"        : "application/vnd.github+json",
        }
    # authenticate for rate limiting
    headers_try_to_add_authorization_from_environment(headers)

    # first fetch the git commit history
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/commits'
    r = requests.get(api_url, headers=headers)
    check_status(r)
    check_rate_limit(r)

    commits = r.json()

    # get runs
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/actions/runs'
    r = requests.get(api_url, headers=headers, params={'per_page': 100})
    check_status(r)
    runs = r.json()
    page_url = get_most_recent_action_page(commits, runs['workflow_runs'])

    return page_url
