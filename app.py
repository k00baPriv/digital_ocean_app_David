import os
import logging
from flask import Flask, redirect, request, jsonify

app = Flask(__name__)

# In-memory storage (replace with database in production)
profiles = {}
subscriptions = {}

# Profile endpoints
@app.route('/api/profile/create-update', methods=['POST'])
def create_profile():
    data = request.get_json()
    
    # Extract the custom field value where field.id is 3358
    custom_field_value = None
    for field in data.get('custom_fields', []):
        if field.get('field', {}).get('id') == 3358:
            custom_field_value = field.get('value')
            break
    
    if custom_field_value is None:
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
    
    return jsonify({
        "member_id": profile['member_id'],
        "trading_view_login": profile['trading_view_login'],
        "username": profile['username'],
        "message": "Profile created / updated successfully"
    }), 200

@app.route('/api/profile/delete', methods=['POST'])
def delete_profile():
    data = request.get_json()
    
    # Check if this is a member deletion event
    if data.get('event') != 'member.deleted':
        return jsonify({"error": "Invalid event type"}), 400
    
    # Get member ID from the payload
    member_id = str(data['member']['id'])

    return jsonify({"message": f"Profile {member_id} deleted successfully"}), 200

# Subscription endpoints
@app.route('/api/subscription/create-update', methods=['POST'])
def create_subscription():
    data = request.get_json()
    
    # Check if this is a subscription creation or update event
    if data.get('event') != 'subscription.created' and data.get('event') != 'subscription.updated':
        return jsonify({"error": "Invalid event type"}), 400
    
    # Extract required fields
    subscription_data = data.get('subscription', {})
    member_id = subscription_data.get('member_id')
    subscription_id = subscription_data.get('id')
    
    # Convert dates to date-only format
    activated_at = subscription_data.get('activated_at', '').split('T')[0] if subscription_data.get('activated_at') else None
    expires_at = subscription_data.get('expires_at', '').split('T')[0] if subscription_data.get('expires_at') else None
    
    # Store the subscription with the required fields
    subscription = {
        'member_id': member_id,
        'subscription_id': subscription_id,
        'activated_at': activated_at,
        'expires_at': expires_at
    }

    return jsonify({
        "member_id": member_id,
        "subscription_id": subscription_id,
        "activated_at": activated_at,
        "expires_at": expires_at,
        "message": "Subscription created / updated successfully"
    }), 201

@app.route('/api/subscription/delete', methods=['POST'])
def delete_subscription():
    data = request.get_json()
    
    # Check if this is a subscription deletion event
    if data.get('event') != 'subscription.deleted':
        return jsonify({"error": "Invalid event type"}), 400
    
    # Get subscription data from the payload
    subscription_data = data.get('subscription', {})
    member_id = subscription_data.get('member_id')
    subscription_id = subscription_data.get('id')
    
    # Convert dates to date-only format
    activated_at = subscription_data.get('activated_at', '').split('T')[0] if subscription_data.get('activated_at') else None
    expires_at = subscription_data.get('expires_at', '').split('T')[0] if subscription_data.get('expires_at') else None
    

    return jsonify({
        "member_id": member_id,
        "subscription_id": subscription_id,
        "activated_at": activated_at,
        "expires_at": expires_at,
        "message": "Subscription deleted successfully"
    }), 200


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    logger = logging.getLogger()

    # Set the log level to DEBUG. This will increase verbosity of logging messages
    logger.setLevel(logging.DEBUG)

    # Add the StreamHandler as a logging handler
    logger.addHandler(logging.StreamHandler())

    app.run(host='0.0.0.0', port=8080)
