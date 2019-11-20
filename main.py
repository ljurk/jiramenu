#!/usr/bin/python3
from jira import JIRA
from rofi import Rofi
from subprocess import Popen, DEVNULL
from os.path import expanduser
import os
import shutil
import configparser
import click


@click.group()
def cli():
    pass


@click.command(help="Runs dmenujira")
@click.option('--debug/--no-debug', default=False)
@click.option('-u','--user',
              help='only show issues that are assigned to given username',
              default=None)
def show(debug, user):
    r = Rofi()
    config = configparser.ConfigParser()
    config.read(expanduser('~/.dmenujira'))

    auth_jira = JIRA(config['JIRA']['url'],
                     basic_auth=(config['JIRA']['user'],
                                 config['JIRA']['password']))

    project_query = 'project=' + config['JIRA']['project']
    if user:
        project_query += " and assignee = " + user
    issues = auth_jira.search_issues(project_query)

    rofi_list = []
    for issue in issues:
        rofi_list.append(issue.key + ':' + issue.fields.summary)
    index, key = r.select('What Issue?', rofi_list, rofi_args=['-i'], width=100)
    if index < 0:
        exit(1)
    ticket_number = rofi_list[index].split(":")[0]

    uri = auth_jira.issue(ticket_number).permalink()
    Popen(['nohup',
          config['JIRA']['browser'], uri],
          stdout=DEVNULL,
          stderr=DEVNULL)


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
