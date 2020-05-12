from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import configparser
import re
import keyring
import click
import pyperclip
from jira import JIRA
from rofi import Rofi

section = 'JIRA'

class jiramenu():
    user = None
    project = None
    auth = None
    config = None
    debug = False
    r = Rofi()
    issues = []
    rofi_list = []

    def __init__(self, config, debug):
        self.config = config
        self.r.status("starting jiramenu")
        try:
            self.auth = JIRA(config['JIRA']['url'],
                             basic_auth=(config['JIRA']['user'],
                                         config['JIRA']['password']))
        except Exception as error:
            self.r.exit_with_error(str(error))
        self.debug = debug

    def log(self, text):
        if not self.debug:
            return
        print(text)

    def show(self, user):
        self.user = user
        self.project = self.config['JIRA']['project']
        if user:
            self.log(f"show issues for: {self.user}")

        query = self.config['JIRA']['query']
        if user:
            query += f" and assignee = '{user}'"
        if self.project:
            query += f" and project = '{self.project}'"
        self.log(f"Query: {query}")
        if not self.issues:
            self.issues = self.auth.search_issues(query)
            self.boards = self.auth.boards()

        if not self.rofi_list:
            if user:
                self.rofi_list.append("> all")
            else:
                self.rofi_list.append("> mine")
            self.issues.sort(key=lambda x: x.fields.status.id, reverse=False)
            for issue in self.issues:
                labels = ''
                if len(issue.fields.labels):
                    labels = '('
                    for idx, label in enumerate(issue.fields.labels):
                        labels += label
                        if idx != len(issue.fields.labels) -1:
                            labels += ', '
                    labels += ')'
                issuetext = ''
                issueassignee = ''
                initials = '  '
                if issue.fields.assignee:
                    issueassignee = issue.fields.assignee.displayName
                    initials = ''.join([x[0].upper() for x in issueassignee.split(' ')])
                if issue.fields.status.id == str(3):  #id:3 = Work in Progress
                    issuetext = '{WIP}'
                issuekey = issue.key
                issuekey = "{:<9}".format(issuekey)
                status = "{:<24}".format(issue.fields.status.name)

                issueassignee = "{:<20}".format(issueassignee)
                issuetext += f'{issuekey} {status} {initials}     {labels} {issue.fields.summary}'
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
        # ticket_number = re.match("IMP-([1-9]|[1-9][0-9])+", self.rofi_list[index]).group(0)
        issue = self.issues[index-1]
        ticket_number = issue.key
        summary = '-'.join(issue.fields.summary.split(' '))
        branch_name= ticket_number + '-' + summary[:33]

        self.log("[details]" + ticket_number)
        issue_description = issue.fields.description

        output = []
        output.append("> show in browser")
        output.append("")
        output.append(f"> copy branch ({branch_name})")
        output.append("")
        output.append("Status: " + self.issues[index - 1].fields.status.name)
        # output.append("Description: " + issue_description)
        description = []
        if issue_description:
            description = issue_description.split('\n')
        for item in description:
            output.append(item)

        if self.auth.comments(ticket_number):
            comment_ids = self.auth.comments(ticket_number)
            for comment_id in comment_ids:
                self.log("comment_id: " + str(comment_id))
                commentauthor = self.auth.comment(ticket_number, comment_id).author.displayName + ':'
                output.append(commentauthor)
                commenttext = self.auth.comment(ticket_number, comment_id).body
                commenttext = commenttext.split('\n')
                for line in commenttext:
                    output.append(line)
        else:
            output.append("no comments")
        output.append("")
        output.append("> add comment")
        output.append("")
        if self.issues[index - 1].fields.assignee:
            output.append("assigned to: " +
                          self.issues[index - 1].fields.assignee.displayName)
        else:
            output.append("> assign to me")

        # if self.issues[index - 1].fields.status.id == str(3):  # WIP
        #     output.append(">>in review")
        # else:
        #     output.append(">>start progress")
        output.append("")
        output.append('< back')
        index, key = self.r.select(ticket_number, output, width=100)
        if index in [-1, len(output) - 1]:
            self.show(user)
            return

        # if index == len(output) - 2:  # move issue to 'In Review'
        #     self.log("[status]"+self.issues[inputIndex - 1].fields.status.name)
        #     self.log("[transitions]")
        #     self.log(self.auth.transitions(ticket_number))
        #     if self.issues[inputIndex - 1].fields.status.id == str(3):  # WIP
        #         for trans in self.auth.transitions(ticket_number):
        #             if trans['name'] == "in Review":
        #                 self.log("move to 'in Review'")
        #                 self.auth.transition_issue(ticket_number, trans['id'])
        #
        #     else:
        #         for trans in self.auth.transitions(ticket_number):
        #             if trans['name'] == "Start Progress":
        #                 self.log("move to 'Start Progress'")
        #                 self.auth.transition_issue(ticket_number, trans['id'])
        #     self.show_details(inputIndex, user)
        #     return

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

        if index == 2:
            pyperclip.copy(branch_name)
            return

        # if index in [3, 4]:
        #     Popen(['notify-send', issue_description, '-t', '30000'])
        #     self.show_details(inputIndex, user)
        #     return

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
@click.option('--browser',
              type=click.STRING,
              prompt=True,
              default="xdg-open")
def configure(dest, url, project, user, password, query, browser):
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
    conf.set(section, 'browser', browser)
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
