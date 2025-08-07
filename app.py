from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from metrics import process_xml, get_latest_metrics, db
import os
import openai  # For ChatGPT-like functionality

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app)

# Initialize OpenAI (optional)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

def process_rrd(filepath):
    """Process RRD files to extract metrics"""
    try:
        import rrdtool
        
        # Example: Extract CPU metrics from RRD
        info = rrdtool.info(filepath)
        
        # Get the last update time and value
        last_update = rrdtool.last(filepath)
        values = rrdtool.fetch(filepath, 'AVERAGE', 
                             f'--start={last_update-300}',  # Last 5 minutes
                             f'--end={last_update}')
        
        # Process the data (example for CPU)
        cpu_avg = sum(values[2][0]) / len(values[2][0]) if values[2][0] else 0
        
        # Store in database
        db.metrics.insert_one({
            "timestamp": datetime.datetime.utcfromtimestamp(last_update),
            "cpu": cpu_avg,
            "memory": psutil.virtual_memory().percent,  # Current as fallback
            "disk": psutil.disk_usage('/').percent,
            "source": "uploaded_rrd"
        })
        
        return f"Processed RRD file. Average CPU: {cpu_avg:.1f}%"
        
    except Exception as e:
        return f"Error processing RRD: {str(e)}"

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.json.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    metrics = get_latest_metrics()
    historical = list(db.metrics.find().sort("timestamp", -1).limit(10))  # Fetch here
    
    # Pass historical data to the response generator
    response = generate_ai_response(question, metrics, historical)  # Updated signature
    
    return jsonify({'response': response})

def generate_ai_response(question, metrics, historical):  # Added historical parameter
    question_lower = question.lower()
    # Rest of your function remains the same
    
    # Memory-specific questions
    if any(word in question_lower for word in ['memory', 'ram', 'usage']):
        alert = " (Warning!)" if metrics['memory'] > 80 else ""
        return f"Current memory usage is {metrics['memory']}%{alert}. " + \
               f"Historical range: {min([m['memory'] for m in historical])}%-{max([m['memory'] for m in historical])}%"
    
    # Disk-specific questions
    elif any(word in question_lower for word in ['disk', 'storage', 'space']):
        return f"Disk usage is at {metrics['disk']}%. " + \
               ("Consider cleaning up files." if metrics['disk'] > 75 else "Space is available.")
    
    # Network-specific questions
    elif any(word in question_lower for word in ['network', 'bandwidth', 'upload']):
        return f"Network data sent: {metrics.get('network', 0)} bytes"
    
    # CPU-specific questions
    elif any(word in question_lower for word in ['cpu', 'processor', 'utilization']):
        return f"CPU is at {metrics['cpu']}% utilization"
    
    # General status questions
    elif any(word in question_lower for word in ['status', 'health', 'overview']):
        return f"""System overview:
        - CPU: {metrics['cpu']}% {'(High load!)' if metrics['cpu'] > 80 else ''}
        - Memory: {metrics['memory']}% {'(Warning!)' if metrics['memory'] > 80 else ''}
        - Disk: {metrics['disk']}% {'(Nearly full!)' if metrics['disk'] > 90 else ''}"""
    
    # Fallback response
    return f"I can report that currently: CPU is at {metrics['cpu']}%, Memory at {metrics['memory']}%, and Disk at {metrics['disk']}%."


@socketio.on('request_update')
def handle_update():
    metrics = get_latest_metrics()
    socketio.emit('data_update', {
        'cpu': metrics['cpu'],
        'memory': metrics['memory'],
        'disk': metrics['disk'],
        'timestamp': metrics['timestamp'].strftime("%H:%M:%S")
    })

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xml', 'rrd'}

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)