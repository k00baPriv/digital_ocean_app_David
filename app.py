import os
import logging
from flask import Flask, redirect, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# In-memory storage (replace with database in production)
profiles = {}
subscriptions = {}

# Profile endpoints
@app.route('/api/profile/insert-update', methods=['POST'])
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
    }), 201

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
@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    data = request.get_json()
    subscription_id = str(len(subscriptions) + 1)
    subscriptions[subscription_id] = data
    return jsonify({"id": subscription_id, "message": "Subscription created successfully"}), 201

@app.route('/api/subscriptions/<subscription_id>', methods=['PUT'])
def update_subscription(subscription_id):
    if subscription_id not in subscriptions:
        return jsonify({"error": "Subscription not found"}), 404
    data = request.get_json()
    subscriptions[subscription_id].update(data)
    return jsonify({"message": "Subscription updated successfully"}), 200

@app.route('/api/subscriptions/<subscription_id>', methods=['DELETE'])
def delete_subscription(subscription_id):
    if subscription_id not in subscriptions:
        return jsonify({"error": "Subscription not found"}), 404
    del subscriptions[subscription_id]
    return jsonify({"message": "Subscription deleted successfully"}), 200


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    logger = logging.getLogger()

    # Set the log level to DEBUG. This will increase verbosity of logging messages
    logger.setLevel(logging.DEBUG)

    # Add the StreamHandler as a logging handler
    logger.addHandler(logging.StreamHandler())

    # Get SSL certificate paths from environment variables
    ssl_cert = os.environ.get('SSL_CERT_PATH')
    ssl_key = os.environ.get('SSL_KEY_PATH')

    if ssl_cert and ssl_key:
        # Run with SSL if certificates are provided
        app.run(host='0.0.0.0', port=8080, ssl_context=(ssl_cert, ssl_key))
    else:
        # Run without SSL if no certificates are provided
        app.run(host='0.0.0.0', port=8080)
