"""
Mock Orders Database for Testing Order Lookup Flow
"""

MOCK_ORDERS = {
    # Easy-to-say order numbers for investor demos
    "111": {
        "order_number": "111",
        "status": "out_for_delivery",
        "status_text": "out for delivery",
        "delivery_date": "today",
        "delivery_time": "by 5pm",
        "delivery_address": "123 Main Street, Boston, MA 02101",
        "tracking_number": "1Z999AA10123456111",
        "items": ["Wireless Headphones", "Phone Case"],
        "total": 79.99
    },
    "123": {
        "order_number": "123",
        "status": "shipped",
        "status_text": "shipped and on the way",
        "delivery_date": "tomorrow",
        "delivery_time": "by end of day",
        "delivery_address": "456 Oak Avenue, San Francisco, CA 94102",
        "tracking_number": "1Z999AA10123456123",
        "items": ["Coffee Maker"],
        "total": 149.99
    },
    "456": {
        "order_number": "456",
        "status": "processing",
        "status_text": "being prepared for shipment",
        "delivery_date": "in 2-3 business days",
        "delivery_time": "",
        "delivery_address": "789 Pine Street, Austin, TX 78701",
        "tracking_number": None,
        "items": ["Running Shoes", "Sports Watch"],
        "total": 229.99
    },
    "789": {
        "order_number": "789",
        "status": "delivered",
        "status_text": "delivered",
        "delivery_date": "yesterday",
        "delivery_time": "at 3:45pm",
        "delivery_address": "321 Elm Drive, Seattle, WA 98101",
        "tracking_number": "1Z999AA10123456789",
        "items": ["Laptop Stand"],
        "total": 59.99
    },
    "999": {
        "order_number": "999",
        "status": "out_for_delivery",
        "status_text": "out for delivery",
        "delivery_date": "today",
        "delivery_time": "by 8pm",
        "delivery_address": "555 Broadway, New York, NY 10012",
        "tracking_number": "1Z999AA10123456999",
        "items": ["Designer Sunglasses", "Leather Wallet"],
        "total": 349.99
    },
    
    # Original orders with added addresses
    "ORDER-12345": {
        "order_number": "ORDER-12345",
        "status": "out_for_delivery",
        "status_text": "out for delivery",
        "delivery_date": "today",
        "delivery_time": "by 5pm",
        "delivery_address": "1600 Pennsylvania Avenue, Washington, DC 20500",
        "tracking_number": "1Z999AA10123456784",
        "items": ["Blue T-Shirt", "Black Jeans"],
        "total": 89.99
    },
    "ORDER-67890": {
        "order_number": "ORDER-67890",
        "status": "processing",
        "status_text": "being prepared for shipment",
        "delivery_date": "in 2-3 business days",
        "delivery_time": "",
        "delivery_address": "350 Fifth Avenue, New York, NY 10118",
        "tracking_number": None,
        "items": ["Running Shoes"],
        "total": 129.99
    },
    "ORDER-54321": {
        "order_number": "ORDER-54321",
        "status": "delivered",
        "status_text": "delivered",
        "delivery_date": "yesterday",
        "delivery_time": "at 2:30pm",
        "delivery_address": "1 Apple Park Way, Cupertino, CA 95014",
        "tracking_number": "1Z999AA10987654321",
        "items": ["Laptop Backpack", "USB Cable"],
        "total": 65.50
    },
    "12345": {
        "order_number": "12345",
        "status": "shipped",
        "status_text": "shipped and on the way",
        "delivery_date": "tomorrow",
        "delivery_time": "by end of day",
        "delivery_address": "1 Infinite Loop, Cupertino, CA 95014",
        "tracking_number": "1Z999AA10111222333",
        "items": ["Wireless Mouse"],
        "total": 29.99
    },
    "67890": {
        "order_number": "67890",
        "status": "cancelled",
        "status_text": "cancelled at your request",
        "delivery_date": None,
        "delivery_time": "",
        "delivery_address": "100 Universal City Plaza, Universal City, CA 91608",
        "tracking_number": None,
        "items": ["Gaming Keyboard"],
        "total": 149.99
    }
}


def lookup_order(order_number_input):
    """
    Look up an order by number (flexible matching)
    
    Args:
        order_number_input: User's input (e.g., "12345", "ORDER-12345", "order 12345")
    
    Returns:
        dict with order info or None if not found
    """
    if not order_number_input:
        return None
    
    clean_input = order_number_input.strip().upper().replace(" ", "").replace("ORDER", "").replace("-", "")
    
    for order_key, order_data in MOCK_ORDERS.items():
        clean_key = order_key.upper().replace("ORDER", "").replace("-", "")
        if clean_input in clean_key or clean_key in clean_input:
            return order_data
    
    return None


def format_order_status(order_data):
    """
    Format order data into a natural speech response
    
    Args:
        order_data: dict with order information
    
    Returns:
        str: Natural language response about the order
    """
    if not order_data:
        return None
    
    order_num = order_data['order_number']
    status_text = order_data['status_text']
    delivery_address = order_data.get('delivery_address', '')
    
    response = f"Your order {order_num} is currently {status_text}."
    
    if order_data['status'] == 'out_for_delivery':
        delivery_time = f" {order_data['delivery_time']}" if order_data['delivery_time'] else ""
        response += f" It should arrive {order_data['delivery_date']}{delivery_time}"
        if delivery_address:
            response += f" at {delivery_address}."
        else:
            response += "."
    
    elif order_data['status'] == 'shipped':
        delivery_time = f" {order_data['delivery_time']}" if order_data['delivery_time'] else ""
        response += f" Expected delivery is {order_data['delivery_date']}{delivery_time}"
        if delivery_address:
            response += f" to {delivery_address}."
        else:
            response += "."
    
    elif order_data['status'] == 'processing':
        response += f" We'll ship it soon"
        if delivery_address:
            response += f" to {delivery_address}"
        response += f", and you should receive it {order_data['delivery_date']}."
    
    elif order_data['status'] == 'delivered':
        response += f" It was delivered {order_data['delivery_date']} {order_data['delivery_time']}"
        if delivery_address:
            response += f" to {delivery_address}."
        else:
            response += "."
    
    elif order_data['status'] == 'cancelled':
        response += " If you have any questions about this, I can connect you with our support team."
    
    return response


def normalize_spoken_numbers(text):
    """
    Convert spoken numbers and comma-separated digits to continuous digit strings
    
    Handles cases like:
    - "one one one" -> "111"
    - "four five six" -> "456"
    - "1, 1, 1" -> "111"
    - "Yes. The order number is 1, 1." -> "Yes. The order number is 11."
    
    Args:
        text: User's spoken input
    
    Returns:
        str: Text with normalized numbers
    """
    import re
    
    # Map of spoken numbers to digits
    number_words = {
        'ZERO': '0', 'OH': '0', 'O': '0',
        'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4', 'FIVE': '5',
        'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9'
    }
    
    text_upper = text.upper()
    
    # First, convert sequences of spoken numbers to digits
    # Match patterns like "ONE ONE ONE" or "FOUR FIVE SIX"
    def replace_spoken_sequence(match):
        words = match.group(0).split()
        digits = ''.join(number_words.get(w, w) for w in words if w in number_words)
        return digits if digits else match.group(0)
    
    # Pattern to match sequences of number words
    spoken_pattern = r'\b(?:ZERO|OH|O|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE)(?:\s+(?:ZERO|OH|O|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE))+\b'
    text_upper = re.sub(spoken_pattern, replace_spoken_sequence, text_upper)
    
    # Also convert single spoken numbers
    for word, digit in number_words.items():
        text_upper = re.sub(r'\b' + word + r'\b', digit, text_upper)
    
    # Remove commas and spaces between digits
    # Match patterns like "1, 1, 1" or "1 1 1" and convert to "111"
    def remove_separators(match):
        return re.sub(r'[,\s]+', '', match.group(0))
    
    # Pattern to match digit sequences with commas/spaces
    digit_separator_pattern = r'\d(?:[,\s]+\d)+'
    text_upper = re.sub(digit_separator_pattern, remove_separators, text_upper)
    
    return text_upper


def extract_order_number_from_speech(speech_text):
    """
    Extract order number from user speech using pattern matching
    
    Args:
        speech_text: User's spoken input
    
    Returns:
        str: Extracted order number or None
    """
    import re
    
    # First normalize spoken numbers to digits
    text = normalize_spoken_numbers(speech_text)
    
    # Support 3-6 digit order numbers
    # Very strict patterns to avoid false positives like "order 20 minutes ago"
    patterns = [
        # 2+ digit patterns - require very explicit order number phrasing
        r'ORDER\s+NUMBER\s+(?:IS\s+)?(\d{2,6})',  # "order number is 11"
        r'ORDER\s+#\s*(\d{2,6})',                 # "order # 11"
        r'NUMBER\s+(?:IS\s+)?(\d{2,6})',          # "number is 456"
        r'#(\d{2,6})',                            # "#123"
        
        # 3+ digit patterns - allow more flexible matching
        r'ORDER[- ]?(\d{3,6})',                   # "order 111" or "order-111"
        r'ORDER\s+(?:IS\s+)?(\d{3,6})',           # "order is 111"
        r'\b(\d{3,6})\b'                          # Standalone 3-6 digit numbers
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None
