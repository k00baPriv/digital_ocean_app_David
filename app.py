import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, request, jsonify
import json
from datetime import datetime

import redis
import ssl


app = Flask(__name__)

# Trading View custom field ID from environment variable
TRADING_VIEW_FIELD_ID = int(os.getenv('TRADING_VIEW_FIELD_ID', '3358'))
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_USERNAME = os.getenv('REDIS_USERNAME', 'default')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'default')


# List of PII fields to mask
PII_FIELDS = {
    'email': '***@***.***',
    'phone_number': '***-***-****',
    'first_name': '***',
    'last_name': '***',
    'full_name': '***',
    'username': '***',
    'stripe_customer_id': '***',
    'discord_user_id': '***',
    'address': {
        'city': '***',
        'country': '***',
        'postal_code': '***',
        'state': '***',
        'street': '***',
        'line2': '***'
    }
}

def mask_pii(data):
    """
    Recursively masks PII data in a dictionary or list
    """
    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if key in PII_FIELDS:
                if isinstance(PII_FIELDS[key], dict) and isinstance(value, dict):
                    masked_data[key] = mask_pii(value)
                else:
                    masked_data[key] = PII_FIELDS[key]
            else:
                masked_data[key] = mask_pii(value)
        return masked_data
    elif isinstance(data, list):
        return [mask_pii(item) for item in data]
    else:
        return data

# Configure logging
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create a rotating file handler
    # Rotate logs every 7 days, keep 4 backup files
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=4,
        encoding='utf-8'
    )
    
    # Create a console handler
    console_handler = logging.StreamHandler()
    
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# In-memory storage (replace with database in production)
profiles = {}
subscriptions = {}

def list_redis_keys(host, port, username, password, use_ssl=True, profile_hash=None, member_id=None):
    print("Listing redis keys")
    try:
        # Connect to Redis
        r = redis.StrictRedis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            ssl=use_ssl,
            ssl_cert_reqs=ssl.CERT_NONE,
            decode_responses=True  # Makes sure you get strings, not bytes
        )

        # If profile_hash and member_id are provided, store them in Redis
        if profile_hash is not None and member_id is not None:
            r.set(member_id, profile_hash)
            logger.info(f"Stored profile hash for member_id: {member_id}")
        else:
            logger.info(f"No profile hash for member_id: {member_id}")

        # Use SCAN to safely get all keys
        cursor = 0
        all_keys = []

        while True:
            cursor, keys = r.scan(cursor=cursor)
            all_keys.extend(keys)
            if cursor == 0:
                break

        return all_keys

    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        return []


@app.before_request
def log_request_info():

    logger.info('Request: %s %s', request.method, request.url)
    logger.info('Headers: %s', dict(request.headers))
    if request.is_json:
        # Mask PII before logging
        masked_data = mask_pii(request.get_json())
        logger.info('Body: %s', json.dumps(masked_data, indent=2))

@app.after_request
def log_response_info(response):
    # Only log response if it's JSON
    if response.headers.get('Content-Type', '').startswith('application/json'):
        try:
            # Mask PII in response before logging
            response_data = json.loads(response.get_data(as_text=True))
            masked_response = mask_pii(response_data)
            logger.info('Response: %s', json.dumps(masked_response, indent=2))
        except json.JSONDecodeError:
            logger.info('Response: %s', response.get_data(as_text=True))
    return response

# Profile endpoints
@app.route('/api/profile/create-update', methods=['POST'])
def create_profile():
    try:
        data = request.get_json()
        logger.info('Processing profile create/update request')
        
        # Extract the custom field value where field.id matches TRADING_VIEW_FIELD_ID
        custom_field_value = None
        for field in data.get('custom_fields', []):
            if field.get('field', {}).get('id') == TRADING_VIEW_FIELD_ID:
                custom_field_value = field.get('value')
                break
        
        if custom_field_value is None:
            logger.warning('Required custom field not found in request')
            return jsonify({"error": "Required custom field not found"}), 400
        
        # Get member ID
        member_id = data['member']['id']
        
        # Create profile hash
        profile_hash = {
            'member_id': str(member_id),
            'username': data['member']['username'],
            'trading_view_login': custom_field_value
        }
        
        # Store profile in Redis
        list_redis_keys(
            REDIS_HOST, 
            REDIS_PORT, 
            REDIS_USERNAME, 
            REDIS_PASSWORD,
            profile_hash=json.dumps(profile_hash),
            member_id=str(member_id)
        )
        
        logger.info('Profile created/updated successfully for member_id: %s', member_id)
        return jsonify({
            "member_id": profile_hash['member_id'],
            "trading_view_login": profile_hash['trading_view_login'],
            "username": profile_hash['username'],
            "message": "Profile created / updated successfully"
        }), 200
    except Exception as e:
        logger.error('Error in create_profile: %s', str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/profile/delete', methods=['POST'])
def delete_profile():
    try:
        data = request.get_json()
        logger.info('Processing profile delete request')
        
        # Check if this is a member deletion event
        if data.get('event') != 'member.deleted':
            logger.warning('Invalid event type in delete profile request')
            return jsonify({"error": "Invalid event type"}), 400
        
        # Get member ID from the payload
        member_id = str(data['member']['id'])
        
        logger.info('Profile deleted successfully for member_id: %s', member_id)
        return jsonify({"message": f"Profile {member_id} deleted successfully"}), 200
    except Exception as e:
        logger.error('Error in delete_profile: %s', str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# Subscription endpoints
@app.route('/api/subscription/create-update', methods=['POST'])
def create_subscription():
    try:
        data = request.get_json()
        logger.info('Processing subscription create/update request')
        
        # Check if this is a subscription creation or update event
        if data.get('event') != 'subscription.created' and data.get('event') != 'subscription.updated':
            logger.warning('Invalid event type in subscription request')
            return jsonify({"error": "Invalid event type"}), 400
        
        # Extract required fields
        subscription_data = data.get('subscription', {})
        member_id = subscription_data.get('member_id')
        subscription_id = subscription_data.get('id')
        
        # Convert dates to date-only format
        activated_at = subscription_data.get('activated_at', '').split('T')[0] if subscription_data.get('activated_at') else None
        expires_at = subscription_data.get('expires_at', '').split('T')[0] if subscription_data.get('expires_at') else None
        
        logger.info('Subscription processed successfully for member_id: %s, subscription_id: %s', member_id, subscription_id)
        return jsonify({
            "member_id": member_id,
            "subscription_id": subscription_id,
            "activated_at": activated_at,
            "expires_at": expires_at,
            "message": "Subscription created / updated successfully"
        }), 200
    except Exception as e:
        logger.error('Error in create_subscription: %s', str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/subscription/delete', methods=['POST'])
def delete_subscription():
    try:
        data = request.get_json()
        logger.info('Processing subscription delete request')
        
        # Check if this is a subscription deletion event
        if data.get('event') != 'subscription.deleted':
            logger.warning('Invalid event type in subscription delete request')
            return jsonify({"error": "Invalid event type"}), 400
        
        # Get subscription data from the payload
        subscription_data = data.get('subscription', {})
        member_id = subscription_data.get('member_id')
        subscription_id = subscription_data.get('id')
        
        # Convert dates to date-only format
        activated_at = subscription_data.get('activated_at', '').split('T')[0] if subscription_data.get('activated_at') else None
        expires_at = subscription_data.get('expires_at', '').split('T')[0] if subscription_data.get('expires_at') else None
        
        logger.info('Subscription deleted successfully for member_id: %s, subscription_id: %s', member_id, subscription_id)
        return jsonify({
            "member_id": member_id,
            "subscription_id": subscription_id,
            "activated_at": activated_at,
            "expires_at": expires_at,
            "message": "Subscription deleted successfully"
        }), 200
    except Exception as e:
        logger.error('Error in delete_subscription: %s', str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
