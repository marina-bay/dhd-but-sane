# See https://pymotw.com/2/multiprocessing/communication.html
import multiprocessing
import os
import subprocess

from compat import *

_current_dir = os.getcwd()


class Consumer(multiprocessing.Process):

    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        while True:
            next_task = self.task_queue.get()
            if next_task is None:
                # Poison pill means shutdown
                self.task_queue.task_done()
                break
            answer = next_task()
            self.task_queue.task_done()
            self.result_queue.put(answer)
        return


class ManageRepoTask(object):
    def __init__(self, package):
        self.url = package['url']
        self.folder_name = package['folder_name']

    def __call__(self):
        manage_git_repo(self.url, self.folder_name)

    def __str__(self):
        return 'url: %s' % (self.url)


def manage_git_repo(url, folder_name):
    _repo_abspath = os.path.join(_current_dir, folder_name)
    if os.path.isdir(_repo_abspath):
        # Only pull updates
        _operation = 'updating'
        print("Updating %s" % folder_name)
        p = subprocess.Popen(
                # -C sets working dir for git
                ['git', '-C', _repo_abspath, 'pull']
        )
    else:
        # Fresh clone
        _operation = 'cloning'
        print("Cloning %s" % url)
        if PY3:
            p = subprocess.Popen(
                  ['git', 'clone', url, folder_name],
                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                  encoding='utf8'  # python3 only
            )
        else:
            p = subprocess.Popen(
                  ['git', 'clone', url, folder_name],
                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            )
    res = p.communicate()
    if res[1]:
        print("Error while %s: %s" % (_operation, res[1]))
    return p.returncode
