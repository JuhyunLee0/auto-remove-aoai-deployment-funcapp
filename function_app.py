import logging
import os
import json
import requests
from datetime import datetime, timezone
import azure.functions as func

# Global variables
base_url = "https://management.azure.com/"
default_api_version = "2022-12-01"
default_ai_service_api_version = "2023-05-01"

# Functions

def is_timestamp_expired(input_timestamp_str):
    # Parse the input timestamp string as UTC
    input_timestamp = datetime.fromisoformat(input_timestamp_str.replace("Z", "+00:00"))
    
    # Get the current time in UTC
    now_utc = datetime.now(timezone.utc)
    
    # Check if the input timestamp is earlier than the current time
    return input_timestamp < now_utc

def get_auth_token():
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "scope": "https://management.azure.com/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # using try to catch the exception
    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.json()["access_token"]
    except Exception as e:
        logging.info(f"Error: {e}")
    return None

def list_subscriptions(auth_token):
    subscription_list = []
    url = f"{base_url}subscriptions"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "api-version": default_api_version
    }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
            
            data = response.json()
            subscription_list.extend(data.get("value", []))  # Add current page's subscriptions to the list
            
            # Check if 'nextLink' exists; if not, we're done
            if 'nextLink' not in data:
                break
                
            # Update the URL for the next iteration with the 'nextLink'
            url = data['nextLink']
            
        except requests.exceptions.HTTPError as http_err:
            logging.info(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.info(f"Request error occurred: {err}")
        except KeyError as ke_err:
            logging.info(f"Key error occurred: {ke_err}")
        
        else:
            continue  # Continue to the next iteration if no exception was raised
        
        break  # Exit the loop if any exception occurs
    
    return subscription_list

def list_resource_groups(auth_token, subscription_id):
    resourcegroup_list = []
    url = f"{base_url}subscriptions/{subscription_id}/resourcegroups"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "api-version": default_api_version
    }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
            
            data = response.json()
            resourcegroup_list.extend(data.get("value", []))  # Add current page's resource groups to the list
            
            # Check if 'nextLink' exists; if not, we're done
            if 'nextLink' not in data:
                break
                
            # Update the URL for the next iteration with the 'nextLink'
            url = data['nextLink']
            
        except requests.exceptions.HTTPError as http_err:
            logging.info(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.info(f"Request error occurred: {err}")
        except KeyError as ke_err:
            logging.info(f"Key error occurred: {ke_err}")
        else:
            continue
        break
    return resourcegroup_list

def list_aoai_services(auth_token, subscription_id, resource_group_name):
    aoai_service_list = []
    url = f"{base_url}subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.CognitiveServices/accounts"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        # "$filter": "kind eq OpenAI",
        "api-version": default_ai_service_api_version
    }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
            
            data = response.json()
            value = data.get("value", [])
            openai_services = list(filter(lambda x: x["kind"] == "OpenAI", value))
            aoai_service_list.extend(openai_services)  # Add current page's resource groups to the list
            
            # Check if 'nextLink' exists; if not, we're done
            if 'nextLink' not in data:
                break
                
            # Update the URL for the next iteration with the 'nextLink'
            url = data['nextLink']
            
        except requests.exceptions.HTTPError as http_err:
            logging.info(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.info(f"Request error occurred: {err}")
        except KeyError as ke_err:
            logging.info(f"Key error occurred: {ke_err}")
        else:
            continue
        break
    return aoai_service_list

def list_aoai_deployments(auth_token, subscription_id, resource_group_name, aoai_service_name):
    deployment_list = []
    url = f"{base_url}subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.CognitiveServices/accounts/{aoai_service_name}/deployments"
    # $filter parameter does not work with this api call
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "api-version": default_ai_service_api_version
    }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
            
            data = response.json()
            value = data.get("value", [])
            # deployment_list.extend(value)
            new_value = list(filter(lambda x: x["sku"]["name"] == "ProvisionedManaged", value))
            deployment_list.extend(new_value)  # Add current page's resource groups to the list
            
            # Check if 'nextLink' exists; if not, we're done
            if 'nextLink' not in data:
                break
                
            # Update the URL for the next iteration with the 'nextLink'
            url = data['nextLink']
            
        except requests.exceptions.HTTPError as http_err:
            logging.info(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.info(f"Request error occurred: {err}")
        except KeyError as ke_err:
            logging.info(f"Key error occurred: {ke_err}")
        else:
            continue
        break
    return deployment_list

def list_aoai_expired_commitment_plans(auth_token, subscription_id, resource_group_name, aoai_service_name):
    commitment_plans = []
    url = f"{base_url}subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.CognitiveServices/accounts/{aoai_service_name}/commitmentPlans"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "api-version": default_ai_service_api_version
    }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
            
            data = response.json()
            values = data.get("value", [])
            for value in values:
                has_expired = is_timestamp_expired(value["properties"]["current"]["endDate"])
                logging.info(has_expired)
                if value["properties"]["autoRenew"] == False and has_expired:
                    commitment_plans.append(value)

            commitment_plans.extend(values)
            
            # Check if 'nextLink' exists; if not, we're done
            if 'nextLink' not in data:
                break
                
            # Update the URL for the next iteration with the 'nextLink'
            url = data['nextLink']
            
        except requests.exceptions.HTTPError as http_err:
            logging.info(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            logging.info(f"Request error occurred: {err}")
        except KeyError as ke_err:
            logging.info(f"Key error occurred: {ke_err}")
        else:
            continue
        break
    return commitment_plans

def delete_aoai_deployments(auth_token, subscription_id, resource_group_name, aoai_service_name, deployment_name):

    # TESTING
    logging.info(f"Deleting deployment {deployment_name}...")
    return
    # TESTING

    url = f"{base_url}subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.CognitiveServices/accounts/{aoai_service_name}/deployments/{deployment_name}"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "api-version": default_ai_service_api_version
    }
    try:
        response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
        logging.info(f"Deployment {deployment_name} deleted successfully.")
    except requests.exceptions.HTTPError as http_err:
        logging.info(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        logging.info(f"Request error occurred: {err}")
    except KeyError as ke_err:
        logging.info(f"Key error occurred: {ke_err}")
    return


# Initialize the function app
app = func.FunctionApp()

@app.schedule(schedule="0 * * * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    logging.info('---------------------- Python timer trigger function started.')
    
     # getting auth token
    token = get_auth_token()

    # listing subscriptions
    # subscriptions = list_subscriptions(token)
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID") if os.getenv("AZURE_SUBSCRIPTION_ID") else ""
    # check if subscription_id is empty
    if subscription_id == "":
        logging.info(f"Subscription ID not given.")
        return
    
    # listing resource groups
    # resource_groups = list_resource_groups(token, subscription_id)
    rg_name = os.getenv("AZURE_RESOURCE_GROUP_NAME") if os.getenv("AZURE_RESOURCE_GROUP_NAME") else ""
    # check if resource group name is empty
    if rg_name == "":
        logging.info(f"Resource Group name not given.")
        return

    # listing all azure openai services
    # aoai_services = list_aoai_services(token, subscription_id, rg_name)
    # alternativly, we can get the aoai_service_name from the environment variable
    aoai_service_name = os.getenv("AZURE_OPENAI_SERVICE_NAME") if os.getenv("AZURE_OPENAI_SERVICE_NAME") else ""

    # getting commitment plan for the service
    commitment_plan_to_check = list_aoai_expired_commitment_plans(token, subscription_id, rg_name, aoai_service_name)

    """
        Assuming that the relationship between the commitment plan and the AOAI resource is 1:1 (meaning that in single AOAI resource, there is only one commitment plan ie. no seperate commitment plan for gpt-3.5 and gpt-4o)
            - this is due to the fact that commiment plan does NOT have any reference to the deployment or the model.
            - the deployment also does NOT have any reference to the commitment plan, other then amount of PTU allocated.
            Q: how are we enforcing the model type when creating deployments for PTU usage?
            e.g. if the commitment plan is for GPT-3.5 (which commitment plan does not have any specification other then the given name), how are we ensuring that the deployment created is also for GPT-3.5?

        we can get the commitment plan list, then all the deployments under that resource
        and if the commitment plan expired, then we can delete all the deployment that is provisionedManaged.
        this is deleting regardless of the model type, version and ptu allocation, bc we are assuming that the commitment plan is 1:1 with the resource.

    """

    # after getting the list of commitment plans, find the corresponding deplouments with the same model.
    for commitment_plan in commitment_plan_to_check:
        # find the deployment with the same name
        aoai_deployments = list_aoai_deployments(token, subscription_id, rg_name, aoai_service_name)
        for deployment in aoai_deployments:
            # may need to do additional check here to make sure to not delete non gpt models.
            logging.info(f"simulating delete deployment: {deployment['name']}")
            # delete_aoai_deployments(token, subscription_id, rg_name, aoai_service_name, deployment["name"])