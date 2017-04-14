import requests
import json
import optparse
import os
from time import sleep
import datetime
from getpass import getpass
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# Disable SSL check warnings from requests module
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def clear_screen():
    # ID OS type.
    os_shell = os.name
    # Clear the shell screen.
    if os_shell == "posix":
        os.system("clear")
        print("\n")
    else:
        os.system("cls")
        print("\n")

# Set up parser and program --help statements.
parser = optparse.OptionParser("Usage: python sod-docverservice_api.py --username <Your LDAP username> --passsword "
                               "<Your LDAP Password> --vm_password <Your VM's password> \n")
parser.add_option("--username", dest="username", type="string", help="This is your AMER LDAP username")
parser.add_option("--password", dest="ldap_password", help="Your LDAP Password")
parser.add_option("--vm_password", dest="vm_password", help="Your VM's Password")
(options, args) = parser.parse_args()

# Verify username is not blank and if it is then clear the screen and post usage message.
if options.username is None:
    clear_screen()
    print(parser.usage)
    exit(1)

# Verify ldap password is not blank and if it is then request it from the user.
if options.ldap_password is None:
    ldap_password = getpass(prompt="Enter your LDAP password: ")
else:
    ldap_password = options.ldap_password

# Verify VM password is not blank and if it is then request it from the user.
if options.vm_password is None:
    vm_password = getpass(prompt="Enter your VM's password: ")
else:
    vm_password = options.vm_password

# Concatenate username with domain name to create User Principal Name (UPN).
upn_username = options.username + "@amer.homedepot.com"

# Create authentication variable for request API calls.
auth_token = (upn_username, ldap_password)

# Base URL
base_url = "https://server.homedepot.com"

order_init_name = "New API order from: {}".format(options.username)

# Json for blank order request.
order_init = {
    "name": "order_init_name",
    "group": "/api/v2/groups/2",
    "submit-now": "false"
}

# Json for service item request (CentOS-7 with Docker).
order_service_item = {
    "service-item-options": {
        "service-item-Update Docker": {},
        "service-item-Install Docker": {},
        "service-item-CentOS7": {
            "environment": "/api/v2/environments/9",
            "attributes": {
                "quantity": 1
            },
            "parameters": {
                "new-password": vm_password,
                "vm-size": "Small (1 x 2)"
            }
        }
    },
    "service-blueprint": "/api/v2/service-blueprints/1",
    "service-name": "CentOS-7 with Docker"
}

# Create a blank order request POST (Step 1).
blank_order_request = requests.post(base_url + '/api/v2/orders/', data=order_init, auth=auth_token, verify=False)
# print(blank_order_request)  #used for testing
if blank_order_request.status_code == 201:
    order_path = blank_order_request.json()['_links']['self']['href']
    # print(order_path)  # used for testing

# Add the service item to the order POST (Step 2).
service_item_add_request = requests.post(base_url + order_path + '/service-items/',
                                         data=json.dumps(order_service_item), auth=auth_token, verify=False,
                                         headers={'Content-Type':'application/json'})

# Submit the order for processing. POST a blank message to /api/v2/orders/<ordernum>/actions/submit/
submit_order_request = requests.post(base_url + order_path + '/actions/submit/', auth=auth_token, verify=False)

# Verify the order was accepted.
if submit_order_request.status_code == 200:
    print("Order Submitted")
else:
    print("There was a problem with your order! The return status code was; {}".format(submit_order_request.status_code))
    exit(1)

# Create While loop to check the order status and then return the server names once the order is complete.
finish_time = datetime.datetime.now() + datetime.timedelta(minutes=120)
server_list = []
finished = False
while not finished:
    now = None
    now = datetime.datetime.now()
    check_status_request = None
    check_status_request = requests.post(base_url + order_path, auth=auth_token, verify=False)
    if check_status_request.json()["status"] == "ACTIVE" and now < finish_time:
        finished = False
        print("Processing your order, please wait..")
        sleep(60)
    elif now > finish_time:
        # Added a time constraint to the loop for run away jobs.
        print("Job has not completed within the two (2) hour time limit")
        exit(1)
    else:
        print("\n Job Status: {}\n".format(check_status_request.json()["status"]))
        for job in check_status_request.json()["_links"]["jobs"]:
            job_end_point = job["href"]
            job_results = requests.post(base_url + job_end_point, auth=auth_token, verify=False)
            if job_results.json()["type"] == "Provision Server":
                server_list.append(job_results.json()["output"].split("hostname")[1].split(".")[0].strip())
        break

for server in server_list:
    print(server)
exit(0)
