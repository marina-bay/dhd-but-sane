# Clone in parallel
# https://stackoverflow.com/questions/26023395/how-to-speed-up-parallelize-downloads-of-git-submodules-using-git-clone-recu/34762036#34762036
# See https://pymotw.com/2/multiprocessing/communication.html
# Update repos if necessary
# May use fixed revisions but discouraged

import multiprocessing
import yaml

from compat import *

import git_manage

DEFAULT_TARGETS_FILE = 'default-mw-targets.yaml'

with open(DEFAULT_TARGETS_FILE, 'r') as f:
    middleware_targets = yaml.safe_load(f)

_packages = []

for item in middleware_targets['common_middlewares']:
    _packages.append(
            {'url': item['url'],
             'folder_name': "hybris/%s" % item['url'].split('/')[-1]}
    )

if __name__ == '__main__':
    # Establish communication queues
    tasks = multiprocessing.JoinableQueue()
    results = multiprocessing.Queue()

    # Start consumers
    #num_consumers = multiprocessing.cpu_count() * 2
    # Better throttle a bit since Github's not happy with many clones at once
    num_consumers = 4
    consumers = [git_manage.Consumer(tasks, results)
                 for i in range(num_consumers)]
    for w in consumers:
        w.start()

    # Enqueue jobs
    num_jobs = len(_packages)
    for i in range(num_jobs):
        tasks.put(git_manage.ManageRepoTask(_packages[i]))

    # Add a poison pill for each consumer
    for i in range(num_consumers):
        tasks.put(None)

    # Wait for all of the tasks to finish
    tasks.join()

    # Start printing results
    while num_jobs:
        result = results.get()
        num_jobs -= 1
