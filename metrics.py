from pymongo import MongoClient
import psutil
import datetime
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client.system_monitor

def init_db():
    """Initialize database with proper indexes"""
    db.metrics.create_index("timestamp")

def collect_metrics():
    db.metrics.insert_one({
        "timestamp": datetime.datetime.utcnow(),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "network": psutil.net_io_counters().bytes_sent,  # Ensure this exists
        "source": "live_metrics"  # Add source field for consistency
    })

# In get_latest_metrics()
def get_latest_metrics():
    result = db.metrics.find_one(sort=[("timestamp", -1)])
    if not result:
        # Return default values if no metrics exist
        return {
            "cpu": 0,
            "memory": 0,
            "disk": 0,
            "network": 0,
            "timestamp": datetime.datetime.utcnow()
        }
    return result

def get_metrics(hours=24):
    """Get metrics from the last N hours"""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    return list(db.metrics.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0, "timestamp": 1, "cpu": 1, "memory": 1, "disk": 1}
    ).sort("timestamp", 1))

def process_xml(filepath):
    """Process XML monitoring files"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Example XML processing - extract CPU metrics
        cpu_metrics = {}
        for ds in root.findall('.//DATASOURCE'):
            name = ds.find('NAME').text
            value = float(ds.find('ACT').text)
            cpu_metrics[name] = value
        
        # Store in database
        db.metrics.insert_one({
            "timestamp": datetime.datetime.utcnow(),
            "cpu": cpu_metrics.get('util', 0),
            "memory": psutil.virtual_memory().percent,  # Current memory as fallback
            "disk": psutil.disk_usage('/').percent,    # Current disk as fallback
            "source": "uploaded_xml"
        })
        
        return f"Processed XML with CPU metrics: {cpu_metrics}"
    
    except Exception as e:
        return f"Error processing XML: {str(e)}"
    
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