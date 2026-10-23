from subprocess import Popen
from threading import Lock
from itertools import count
from uuid import uuid4

class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """

    _instances = {}

    _lock: Lock = Lock()
    """
    We now have a lock object that will be used to synchronize threads during
    first access to the Singleton.
    """

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        # Now, imagine that the program has just been launched. Since there's no
        # Singleton instance yet, multiple threads can simultaneously pass the
        # previous conditional and reach this point almost at the same time. The
        # first of them will acquire lock and will proceed further, while the
        # rest will wait here.
        with cls._lock:
            # The first thread to acquire the lock, reaches this conditional,
            # goes inside and creates the Singleton instance. Once it leaves the
            # lock block, a thread that might have been waiting for the lock
            # release may then enter this section. But since the Singleton field
            # is already initialized, the thread won't create a new object.
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Job:
    """A job process"""

    id: str
    number: int
    job_process: Popen
    command: str
    marker: str
    status: str

    def __init__(self, job_id: str, number: int, job_process: Popen,  command: str, marker: str = "+"):
        """Constructor of Job class."""
        self.id = job_id
        self.number = number
        self.job_process = job_process
        self.command = command
        self.marker = marker
        self.set_status(job_process)

    def __str__(self) -> str:
        """String representation of the job."""
        self.refresh()
        space_to_command = 24
        status = self.status
        spaces = space_to_command - len(status)

        return f"[{self.number}]{self.marker}  {status}" + " " * spaces + self.command

    def refresh(self) -> None:
        """Polls the process to refresh its returncode."""
        self.job_process.poll()
        self.set_status(self.job_process)

    def set_status(self, job_process: Popen) -> None:
        """Gets the current status of the job by checking the process."""
        return_code = job_process.poll()
        if return_code is None:
            self.status="Running"
            return

        if return_code is not None and return_code < 0:
            self.status="Failed"
            return

        self.status="Done"
        


class JobManager(metaclass=SingletonMeta):
    """
    Job manager stores and keeps tracks of jobs. 
    Singleton so its reachable from anywhere and can be updated anywhere.
    """

    _instance = None
    _jobs: list[Job]
    _job_lookup: dict[str, int]

    def __init__(self):
        self._jobs = []
        self._job_lookup = {}
        self._job_counter = count(1)

    def register_job(self, process: Popen, command: str) -> int:
        """Registers a job."""
        job_id = str(uuid4())
        job_num = next(self._job_counter)
        new_job = Job(job_id, job_num, process, command=command)
        if self._jobs:
            self._jobs[-1].marker = "-"
            if len(self._jobs) > 1:
                self._jobs[-2].marker = " "

        self._jobs.append(new_job)
        self._job_lookup[job_id] = len(self._jobs) - 1
        return job_num

    def get_jobs(self) -> list[Job]:
        """Returns all registered jobs."""
        self._refresh()
        return self._jobs

    def _refresh(self) -> None:
        """Refreshes all jobs."""
        [job.refresh() for job in self._jobs]

    def remove_job(self, job_id: str) -> Job | None:
        """Removes/kills a job process."""
        job_idx = self._job_lookup.get(job_id)
        if not (job_idx is None):
            return self._jobs.pop(job_idx)