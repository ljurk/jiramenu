#!/usr/bin/python3
from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import shutil
import configparser
import click
from jira import JIRA
from rofi import Rofi

class dmenujira():
    user = None
    auth = None
    config = None
    debug = False
    r = Rofi()
    issues = []
    rofi_list = []

    def __init__(self, config, debug):
        self.config = config
        self.auth = JIRA(config['JIRA']['url'],
                         basic_auth=(config['JIRA']['user'],
                                     config['JIRA']['password']))
        self.debug = debug

    def show(self, user):
        self.user = user
        if self.debug:
            print(self.user)

        project_query = 'project=' + self.config['JIRA']['project']
        if user:
            project_query += " and assignee = " + user
        if self.debug:
            print("Query: " + project_query)
        if not self.issues:
            self.issues = self.auth.search_issues(project_query)

        if not self.rofi_list:
            for issue in self.issues:
                self.rofi_list.append(issue.key + ':' + issue.fields.summary)
        index = self.r.select('What Issue?', self.rofi_list, rofi_args=['-i'], width=100)
        if index < 0:
            exit(1)
        self.show_details(index, user)


    def show_details(self, index, user):
        ticket_number = self.rofi_list[index].split(":")[0]
        issue_description = self.issues[index].fields.description
        output = []
        output.append(">>show in browser")
        output.append(">>description")
        output.append(issue_description)
        if self.auth.comments(ticket_number):
            output.append(">>comments")
            comment_ids = self.auth.comments(ticket_number)
            for comment_id in comment_ids:
                if self.debug:
                    print("comment_id: " + str(comment_id))
                output.append(self.auth.comment(ticket_number, comment_id).body)
        else:
            output.append("no comments")

        output.append(">>in review")
        output.append('<<back')
        index, key= self.r.select(ticket_number, output, width=100)
        if index in [-1, len(output) - 1]:
            self.show(user)

        if index == len(output) - 2:  # move issue to 'In Review'
            self.auth.transition_issue(ticket_number, '721')  # 721 is the id of 'In Review'

        if index == 0:  # show in browser
            uri = self.auth.issue(ticket_number).permalink()
            Popen(['nohup', self.config['JIRA']['browser'], uri],
                  stdout=DEVNULL,
                  stderr=DEVNULL)


@click.group()
def cli():
    pass


@click.command(help="Runs dmenujira")
@click.option('--debug/--no-debug', default=False)
@click.option('-u', '--user',
              help='only show issues that are assigned to given username',
              default=None)
def show(debug, user):
    if debug:
        print("DEBUG MODE")
    config = configparser.ConfigParser()
    config.read(expanduser('~/.dmenujira'))
    temp = dmenujira(config, debug)
    temp.show(user)


@cli.command(help="creates sample config file")
@click.option("-d", "--dest",
              required=False,
              type=click.Path(),
              default=expanduser("~/.dmenujira"))
def copy_config(dest):
    if os.path.exists(dest):
        raise click.UsageError("Config already exists in {}".format(dest))
    dest_dir = os.path.dirname(dest)
    if not os.path.exists(dest_dir):
        raise click.UsageError("Directory doesn't exist: {}".format(dest_dir))

    click.echo("Creating config in {}".format(dest))
    shutil.copy("./dmenujira.conf", dest)


cli.add_command(show)
cli.add_command(copy_config)

if __name__ == '__main__':
    cli()
