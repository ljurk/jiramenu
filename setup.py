from setuptools import setup

setup(
    name='jiramenu',
    version='1.0.0',
    packages=['jiramenu'],
    author="Lukas Jurk",
    author_email="ljurk@pm.me",
    description="dmenu/rofi frontend for jira",
    long_description=open('readme.md').read(),
    long_description_content_type="text/markdown",
    license="GPLv3",
    keywords="jira dmenu rofi",
    url="https://github.com/ljurk/jiramenu",
    entry_points={
        'console_scripts': ['jiramenu=jiramenu.jiramenu:cli']
    },
    install_requires=[
        "jira",
        "python-rofi",
        "requests",
        "Click"
    ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ]
)
