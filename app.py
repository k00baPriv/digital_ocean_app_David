import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Trading View custom field ID from environment variable
TRADING_VIEW_FIELD_ID = int(os.getenv('TRADING_VIEW_FIELD_ID', '3358'))

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
        
        # Store the profile with the custom field value
        profile_id = str(member_id)
        profile = {
            'member_id': profile_id,
            'username': data['member']['username'],
            'trading_view_login': custom_field_value
        }
        
        logger.info('Profile created/updated successfully for member_id: %s', member_id)
        return jsonify({
            "member_id": profile['member_id'],
            "trading_view_login": profile['trading_view_login'],
            "username": profile['username'],
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
