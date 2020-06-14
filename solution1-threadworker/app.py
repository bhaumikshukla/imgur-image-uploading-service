#!flask/bin/python
from flask import Flask, jsonify
from flask import request
import settings
import uuid
import base64
from imgurpython import ImgurClient
from task import uploading_task, records, imgur_urls_list
import json
import pytz
import datetime
import threading

'''
processThread = threading.Thread(target=processLine, args=(dRecieved,))  # <- note extra ','
processThread.start()
'''

app = Flask(__name__)

app.config.from_object(settings)

# vars
localpath = app.config['LOCALFILEPATH']

'''
REST APIs
'''

'''
Image uploading REST POST API
It accepts URL list from requests and start assigning the asynchronous jobs to Celery Workers. 
'''
@app.route('/v1/images/upload', methods=['POST'])
def create_job():
    #check if param is provided & properly or not
    if not request.json or not 'urls' in request.json:
    	return jsonify({"error":"param 'urls' not found in json or json has not been prepared properly"}), 400

    # Preparing a list
    urls = request.json["urls"]
    # creating unique id of parent job
    job_id = str(uuid.uuid1())

    # creating datetime in ISO 8601 format (UTC)
    utc_now = pytz.utc.localize(datetime.datetime.utcnow().replace(microsecond=0))
    timestamp = utc_now.isoformat()
    # storing job info i.e. create ts 
    records["imgur_create_ts_" + job_id] = timestamp

    # init subtask (for each url) list
    subtasks = []
    #loop it around
    for url in urls:
    	# Assigning upload task for each seperate URL
    	new_task_id = str(uuid.uuid1())

    	# initiate the task with PENDING status
    	records["imgur_subtask_status_" + new_task_id] = "PENDING"
    	# Assigning the uploading job to thread, opens a new thread to each url download & upload task
    	processThread = threading.Thread(target=uploading_task, args=(url, job_id, new_task_id))
    	processThread.start()

    	# preparing a task json
    	task_dict = {
    	"url": url,
    	"task_id": new_task_id
    	}
    	# appending a dict of single task info to subtasks list
    	subtasks.append(task_dict)

    #preparing json to be stored as value of parent task signature
    d = {
    	"subtasks": subtasks
    }
    # storing in dict, only executes when it's success
    records["imgur_" + job_id] = json.dumps(d)

    # returning the response
    return jsonify({"jobId":job_id}), 201

# TODO:  wanted to use the validator with uploading API, later.
def urlvalidator(url):
	pass

'''
API to get complete status of job, it includes status of master jobs and uploading stats of each URL.
To achieve, it fetches data from dict w.r.t. master job and subtasks i.e. each URL tasks and celery job status,
later it prepares the response and return as json
'''
@app.route('/v1/images/upload/<string:jobId>', methods=['GET'])
def get_tasks(jobId):
	# validate the Job ID by fetching timestamp of given job
	try:
	    ts = records["imgur_create_ts_" + jobId]
	except KeyError as e:
		ts = None


	if ts is None:
		return jsonify({"error": "Provided 'jobID' does not exist."}), 400

	# success, failed lists init
	completed = []
	failed = []
	pending = []
	finished = None
	status = "pending"
	# fetching subtasks i.e. Celery Tasks' IDS assigned to get things uploaded for each URL
	lst_subtasks = records["imgur_" + str(jobId)]
	#preparing it in dict
	d_obj = json.loads(lst_subtasks)

	# for each task, need to fetch the status and details
	for ele in d_obj["subtasks"]:
		# check if task has been successful
		# result = uploading_task.AsyncResult(str(ele["task_id"]))
		result = records["imgur_subtask_status_" + str(ele["task_id"])]
		if result == "SUCCESS":
			completed.append(ele["url"])
		elif result == "FAILURE":
			failed.append(ele["url"])
		else:
			pending.append(ele["url"])

	# deciding status & finished flags
	if len(pending) == 0:
		finished = True
		status = "completed"
	else:
		status = "in-progress"

	if len(completed) == 0 and len(failed) == 0:
		status = "pending"

	# preparing the response json
	res = {
	"id": jobId,
	"created" : ts,
	"finished": finished,
	"status":  status,
	"uploaded" :  {
		"pending": pending,
		"complete": completed,
		"failed": failed
		}
	}

	# returning the respoonse		
	return jsonify(res), 200

'''
API to serve all the uploaded videos to imgur.
It fetches all the URLs & items which are successfully uploaded
'''
@app.route('/v1/images', methods=['GET'])
def get_images():
	
	# Preparing list (for response)
	linkURLs = []

	# fetching all the items i.e. successful uploaded URL from list imgur_urls_list
	# iter from each item
	for ele in imgur_urls_list:
		# appending the value i.e. final imgur URL
		linkURLs.append(imgur_urls_list[ele])

	#preparing the response
	res = {
		"uploaded" : linkURLs
	}
	# returning the response
	return jsonify(res), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
