#!/usr/bin/python3

from jira import JIRA
from rofi import Rofi
from subprocess import Popen, DEVNULL
from os.path import expanduser
import configparser

r = Rofi()
config = configparser.ConfigParser()
config.read(expanduser('~/.dmenujira'))

auth_jira = JIRA(config['JIRA']['url'], basic_auth=(config['JIRA']['user'], config['JIRA']['password']))

project_query = 'project=' + config['JIRA']['project']
issues = auth_jira.search_issues(project_query)

rofi_list = []
for issue in issues:
    rofi_list.append(issue.key + ':' + issue.fields.summary)
index, key = r.select('What Issue?', rofi_list, rofi_args=['-i'])    
if index < 0:
    exit(1)
ticket_number = rofi_list[index].split(":")[0]

uri = auth_jira.issue(ticket_number).permalink()
Popen(['nohup', config['JIRA']['browser'], uri], stdout=DEVNULL, stderr=DEVNULL)
