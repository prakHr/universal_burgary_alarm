# universal_burgary_alarm
Uses state diagram and multiple personas based security alarm

# how to install it
pip install universal-burglary-alarm==0.2.0

# Sample code to run it
from universal_alarm import *

    incident_dict = {
        "Burglary": 0.001,
        "Earthquake": 0.002,
        "Alarm_nonBurglarynonEarthquake": 0.001,
        "Alarm_BurglarynonEarthquake": 0.29,
        "Alarm_nonBurglaryEarthquake": 0.94,
        "Alarm_BurglaryEarthquake": 0.95
    }

    hearing_dict = {
        "John": {"nonAlarm": 0.1, "Alarm": 0.9},
        "Mary": {"nonAlarm": 0.2, "Alarm": 0.8},
        "Alice": {"nonAlarm": 0.15, "Alarm": 0.85},
        "Bob": {"nonAlarm": 0.25, "Alarm": 0.75},
        "Eve": {"nonAlarm": 0.05, "Alarm": 0.95}
    }
    
    qc, labels = universal_alarm(incident_dict, hearing_dict)
    app,check = get_app(qc, labels)
    if check == True:
        app.run_server(debug=True)

    hearing_dict = {
        f"person_{i}": {"nonAlarm": random.uniform(0.1, 0.3), "Alarm": random.uniform(0.8, 0.9)}
        for i in range(100)
    }
    qc, labels = universal_alarm(incident_dict, hearing_dict)
    app,check = get_app(qc, labels)
    if check == True:
        app.run_server(debug=True)

    hearing_dict = {
        f"person_{i}": {"nonAlarm": random.uniform(0.1, 0.3), "Alarm": random.uniform(0.8, 0.9)}
        for i in range(1000_000)
    }
    qc, labels = universal_alarm(incident_dict, hearing_dict)
    app,check = get_app(qc, labels)
    if check == True:
        app.run_server(debug=True)

    
