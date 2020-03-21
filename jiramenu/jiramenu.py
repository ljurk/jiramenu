#!/usr/bin/python3
from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import shutil
import configparser
import re
import click
from jira import JIRA
from rofi import Rofi

class jiramenu():
    user = None
    auth = None
    config = None
    debug = False
    r = Rofi()
    issues = []
    rofi_list = []

    def __init__(self, config, debug):
        self.config = config
        self.r.status("starting jiramenu")
        self.auth = JIRA(config['JIRA']['url'],
                         basic_auth=(config['JIRA']['user'],
                                     config['JIRA']['password']))
        self.debug = debug

    def log(self, text):
        if not self.debug:
            return
        print(text)

    def show(self, user):
        self.user = user
        if user:
            self.log("show issues for:" + self.user)

        project_query = 'status not in ("closed", "Gelöst")'
        project_query += 'and project=' + self.config['JIRA']['project']
        if user:
            project_query += " and assignee = " + user
        self.log("Query: " + project_query)
        if not self.issues:
            self.issues = self.auth.search_issues(project_query)

        if not self.rofi_list:
            if user:
                self.rofi_list.append(">>ALL")
            else:
                self.rofi_list.append(">>MINE")
            for issue in self.issues:
                issuetext = ''
                if issue.fields.assignee:
                    issuetext = '[' + issue.fields.assignee.name + ']'
                if issue.fields.status.id == str(3):  #id:3 = Work in Progress
                    issuetext += '{WIP}'
                issuetext += issue.key + ':' + issue.fields.summary
                self.rofi_list.append(issuetext)

        index, key = self.r.select(project_query + '[' + str(len(self.rofi_list)) + ']', self.rofi_list, rofi_args=['-i'], width=100)
        if index < 0:
            exit(1)
        if index == 0:
            self.issues = []
            self.rofi_list = []
            if user:
                self.show(None)
            else:
                self.show(self.config['JIRA']['user'])
            return
        self.show_details(index, user)

    def addComment(self, ticket_number):
        comment = self.r.text_entry("Content of the comment:")
        if comment:
            # replace @user with [~user]
            comment = re.sub(r"@(\w+)", r"[~\1]", comment)
            self.auth.add_comment(ticket_number, comment)

    def show_details(self, index, user):
        inputIndex = index
        ticket_number = re.sub(r"\[.*\]", "", self.rofi_list[index])
        ticket_number = re.sub(r"\{.*\}", "", ticket_number)
        ticket_number = ticket_number.split(":")[0]
        self.log("[details]" + ticket_number)
        issue_description = self.issues[index - 1].fields.description

        output = []
        output.append(">>show in browser")
        output.append("[[status]]")
        output.append(self.issues[index - 1].fields.status.name)
        output.append("[[description]]")
        output.append(issue_description)

        if self.auth.comments(ticket_number):
            output.append("[[comments]]")
            comment_ids = self.auth.comments(ticket_number)
            for comment_id in comment_ids:
                self.log("comment_id: " + str(comment_id))
                commenttext = '[' + self.auth.comment(ticket_number, comment_id).author.name + ']'
                commenttext += self.auth.comment(ticket_number, comment_id).body
                output.append(commenttext)
        else:
            output.append("[[no comments]]")
        output.append(">>add comment")
        if self.issues[index - 1].fields.assignee:
            output.append("[[assignee]]" +
                          self.issues[index - 1].fields.assignee.name)
        else:
            output.append(">>assign to me")

        if self.issues[index - 1].fields.status.id == str(3):  # WIP
            output.append(">>in review")
        else:
            output.append(">>start progress")

        output.append('<<back')
        index, key = self.r.select(ticket_number, output, width=100)
        if index in [-1, len(output) - 1]:
            self.show(user)
            return

        if index == len(output) - 2:  # move issue to 'In Review'
            self.log("[status]"+self.issues[inputIndex - 1].fields.status.name)
            self.log("[transitions]")
            self.log(self.auth.transitions(ticket_number))
            if self.issues[inputIndex - 1].fields.status.id == str(3):  # WIP
                for trans in self.auth.transitions(ticket_number):
                    if trans['name'] == "in Review":
                        self.log("move to 'in Review'")
                        self.auth.transition_issue(ticket_number, trans['id'])

            else:
                for trans in self.auth.transitions(ticket_number):
                    if trans['name'] == "Start Progress":
                        self.log("move to 'Start Progress'")
                        self.auth.transition_issue(ticket_number, trans['id'])
            self.show_details(inputIndex, user)
            return

        if index == len(output) - 4:  # add comment
            self.log("[addComment]")
            self.addComment(ticket_number)
            self.show_details(inputIndex, user)
            return

        if index == len(output) - 3:  # assign to me
            self.log("[assign to me]")
            self.auth.assign_issue(ticket_number, self.config['JIRA']['user'])
            self.show_details(inputIndex, user)
            return

        if index in [3, 4]:
            Popen(['notify-send', issue_description, '-t', '30000'])
            self.show_details(inputIndex, user)
            return

        # show in browser
        self.log("[show in browser]")
        uri = self.auth.issue(ticket_number).permalink()
        Popen(['nohup', self.config['JIRA']['browser'], uri],
              stdout=DEVNULL,
              stderr=DEVNULL)


@click.group()
def cli():
    pass


@click.command(help="Runs jiramenu")
@click.option('--debug/--no-debug', default=False)
@click.option('-u', '--user',
              help='only show issues that are assigned to given username',
              default=None)
def show(debug, user):
    if debug:
        print("DEBUG MODE")
    config = configparser.ConfigParser()
    config.read(expanduser('~/.jiramenu'))
    temp = jiramenu(config, debug)
    temp.show(user)


@cli.command(help="creates sample config file")
@click.option("-d", "--dest",
              required=False,
              type=click.Path(),
              default=expanduser("~/.jiramenu"))
def copy_config(dest):
    if os.path.exists(dest):
        raise click.UsageError("Config already exists in {}".format(dest))
    dest_dir = os.path.dirname(dest)
    if not os.path.exists(dest_dir):
        raise click.UsageError("Directory doesn't exist: {}".format(dest_dir))

    click.echo("Creating config in {}".format(dest))
    shutil.copy("./jiramenu.conf", dest)


cli.add_command(show)
cli.add_command(copy_config)

if __name__ == '__main__':
    cli()
