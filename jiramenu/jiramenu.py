from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import configparser
import re
import keyring
import click
from jira import JIRA
from rofi import Rofi

section = 'JIRA'

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
            self.log(f"show issues for: {self.user}")

        query = self.config['JIRA']['query']
        if user:
            query += f" and assignee = {user}"
        self.log(f"Query: {query}")
        if not self.issues:
            self.issues = self.auth.search_issues(query)

        if not self.rofi_list:
            if user:
                self.rofi_list.append(">>ALL")
            else:
                self.rofi_list.append(">>MINE")
            for issue in self.issues:
                issuetext = ''
                if issue.fields.assignee:
                    issuetext = f'[{issue.fields.assignee.name}]'
                if issue.fields.status.id == str(3):  #id:3 = Work in Progress
                    issuetext += '{WIP}'
                issuetext += f'{issue.key}:{issue.fields.summary}'
                self.rofi_list.append(issuetext)

        # print active query plus number of results on top
        index, key = self.r.select(f'{query}[{len(self.rofi_list)}]',
                                   self.rofi_list,
                                   rofi_args=['-i'],
                                   width=100)
        del key
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
@click.version_option()
def cli():
    pass


@click.command(help="Runs jiramenu")
@click.option('--debug/--no-debug', default=False)
@click.option('-u', '--user',
              help='only show issues that are assigned to given username',
              default=None)
@click.option('-c', '--config',
              default=expanduser('~/.config/jiramenu/config'),
              type=click.Path(exists=True))
def show(debug, user, config):
    if debug:
        print("DEBUG MODE")
    conf = configparser.ConfigParser()
    conf.read(config)

    #get password from keyring
    conf.set(section, 'password', keyring.get_password('jiramenu', conf[section]['user']))

    temp = jiramenu(conf, debug)
    temp.show(user)


@cli.command(help="creates config file")
@click.option("-d", "--dest",
              required=True,
              type=click.Path(),
              default=expanduser('~/.config/jiramenu/config'))
@click.option('--url',
              type=click.STRING,
              prompt=True)
@click.option('--project',
              type=click.STRING,
              prompt=True)
@click.option('--user',
              type=click.STRING,
              prompt=True)
@click.password_option(help='the password will be saved inside default gnome-keyring')
@click.option('--query',
              type=click.STRING,
              prompt=True,
              default="status not in ('closed', 'Gelöst')")
def configure(dest, url, project, user, password, query):
    if not os.path.exists(os.path.dirname(dest)):
        os.mkdir(os.path.dirname(dest))

    conf = configparser.ConfigParser()
    print(url)
    print(type(url))
    conf.add_section(section)
    conf.set(section, 'url', str(url))
    conf.set(section, 'project', project)
    conf.set(section, 'user', user)
    conf.set(section, 'query', query)
    #save password to keyring
    keyring.set_password('jiramenu', user, password)
    click.echo("Creating config in {}".format(dest))
    #write to config file
    with open(dest, 'w') as filestream:
        conf.write(filestream)


cli.add_command(show)
cli.add_command(configure)

if __name__ == '__main__':
    cli()
