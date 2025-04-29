from setuptools import setup, find_packages

def read_requirements():
    """Read dependencies from requirements.txt"""
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="task-scheduler-x",
    version="1.0.26",
    author="Samuel Longauer",
    author_email="samuel.longauer@gmail.com",
    description="A CLI-based Task Scheduling Application",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/longauer/task_scheduler",
    packages=find_packages(),
    install_requires= [
        "argparse",
        "datetime",
        "colorama",
        "urwid"
],
    entry_points={
        "console_scripts": [
            "task-scheduler=task_scheduler.main:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
