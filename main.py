#!/usr/bin/python3
from jira import JIRA
from rofi import Rofi
from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import shutil
import configparser
import click

class dmenujira():
    user = None
    auth = None
    config = None
    r = Rofi()
    issues = []
    rofi_list = []
    def __init__(self, config):
        self.config = config
        self.auth = JIRA(config['JIRA']['url'],
                         basic_auth=(config['JIRA']['user'],
                                     config['JIRA']['password']))

    def show(self, user):
        self.user = user
        print("ok")
        print(self.user)

        project_query = 'project=' + self.config['JIRA']['project']
        if user:
            project_query += " and assignee = " + user
        print(project_query)
        if len(self.issues) == 0:
            self.issues = self.auth.search_issues(project_query)

        if len(self.rofi_list) == 0:
            for issue in self.issues:
                self.rofi_list.append(issue.key + ':' + issue.fields.summary)
        index, key = self.r.select('What Issue?', self.rofi_list, rofi_args=['-i'], width=100)
        if index < 0:
            exit(1)
        self.show_details(index, user)

        #return index, rofi_list, issues

    def show_details(self, index, user):
        print("ok")
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
                print(comment_id)
                output.append(self.auth.comment(ticket_number, comment_id).body)
        else:
            output.append( "no comments")

        output.append('<<back')
        #output.append(issue_comments)
        index, key= self.r.select('option', output, width=100)
        if index in [-1, len(output) - 1]:
            self.show(user)
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
@click.option('-u','--user',
              help='only show issues that are assigned to given username',
              default=None)
def show(debug, user):
    if debug:
        print("DEBUG MODE")
    config = configparser.ConfigParser()
    config.read(expanduser('~/.dmenujira'))
    temp = dmenujira(config)
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
