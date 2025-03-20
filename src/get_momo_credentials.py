import requests
import uuid
import os
from dotenv import load_dotenv
load_dotenv()

def get_momo_credentials():
    """
    Get MTN MoMo sandbox credentials by creating a new user
    """
    # Sandbox API Key (this is the default sandbox key)
    API_KEY = os.getenv('MTN_SANDBOX_API_KEY')
    
    # Base URL for sandbox
    BASE_URL = "https://sandbox.momodeveloper.mtn.com"
    
    # Generate a unique reference ID
    reference_id = str(uuid.uuid4())
    
    # Headers for API requests
    headers = {
        'X-Reference-Id': reference_id,
        'X-Target-Environment': 'sandbox',
        'Ocp-Apim-Subscription-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Step 1: Create API User
        print("Creating API User...")
        user_payload = {
            "providerCallbackHost": "https://webhook.site/b73d348f-f37a-4e3a-aabb-bb756110cc5b"
        }
        
        response = requests.post(
            f"{BASE_URL}/v1_0/apiuser",
            headers=headers,
            json=user_payload
        )
        response.raise_for_status()
        print("API User created successfully!")
        
        # Step 2: Get API Key
        print("\nGetting API Key...")
        response = requests.post(
            f"{BASE_URL}/v1_0/apiuser/{reference_id}/apikey",
            headers=headers
        )
        response.raise_for_status()
        api_key = response.json().get('apiKey')
        print(f"API Key: {api_key}")
        
        # Step 3: Create OAuth Token
        #print("\nCreating OAuth Token...")
        #auth_headers = {
        #    'X-Reference-Id': reference_id,
        #    'X-Target-Environment': 'sandbox',
        #    'Ocp-Apim-Subscription-Key': API_KEY,
        #    'Authorization': f'Basic {api_key}',
        #    'X-OAuth-Token': 'Basic',
        #    'Content-Type': 'application/json'
        #}
        
        #response = requests.post(
        #    f"{BASE_URL}/collection/token/",
        #    headers=auth_headers
        #)
        #response.raise_for_status()
        #access_token = response.headers.get('X-OAuth-Token')
        #print(f"Access Token: {access_token}")
        
        # Save credentials to .env file
        print("\nSaving credentials to .env file...")
        env_content = f"""
        MTN_MOMO_API_KEY={api_key}
        MTN_MOMO_USER_ID={reference_id}
        MTN_MOMO_PRIMARY_KEY={API_KEY}
        """
        #MTN_MOMO_ACCESS_TOKEN={access_token}
        
        with open('.env', 'a') as f:
            f.write(env_content)
        print("Credentials saved to .env file!")
        
        return {
            'api_key': api_key,
            'user_id': reference_id,
            'primary_key': API_KEY,
            #'access_token': access_token
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

if __name__ == "__main__":
    print("Starting MTN MoMo Sandbox Credentials Setup...")
    credentials = get_momo_credentials()
    
    if credentials:
        print("\nSetup completed successfully!")
        print("\nCredentials Summary:")
        print(f"User ID: {credentials['user_id']}")
        print(f"API Key: {credentials['api_key']}")
        print(f"Primary Key: {credentials['primary_key']}")
        #print(f"Access Token: {credentials['access_token']}")
        
        print("\nYou can now use these credentials with the MTNMoMo class:")
        print("""
momo = MTNMoMo(
    api_key='your_api_key',
    user_id='your_user_id',
    primary_key='your_primary_key',
    environment='sandbox'
)
""") 