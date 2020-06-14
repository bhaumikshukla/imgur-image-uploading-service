#!flask/bin/python
from flask import Flask, jsonify
from flask import request
import settings
from celery import Celery
import uuid
import redis
import base64
from imgurpython import ImgurClient
from task import uploading_task
import json
import pytz
import datetime

app = Flask(__name__)

app.config.from_object(settings)

# for in-mem storage
redisobj = redis.StrictRedis(host='localhost', port=6379, db=0)
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
    # storing job info i.e. create ts in redis
    redisobj.set("imgur_create_ts_" + job_id, timestamp)
    # init subtask (for each url) list
    subtasks = []

    #loop it around
    for url in urls:
    	# Assigning upload task for each seperate URL
    	task = uploading_task.apply_async(args=[url, job_id]) # passing the jobId alsong for signature
    	# preparing a task json
    	task_dict = {
    	"url": url,
    	"task_id": task.id
    	}
    	# appending a dict of single task info to subtasks list
    	subtasks.append(task_dict)

    #preparing json to be stored as value of parent task signature
    d = {
    	"subtasks": subtasks
    }
    # storing in redis, only executes when it's success
    redisobj.set("imgur_" + job_id, json.dumps(d))
    # returning the response
    return jsonify({"jobId":job_id}), 201

# TODO:  wanted to use the validator with uploading API, later.
def urlvalidator(url):
	pass

'''
API to get complete status of job, it includes status of master jobs and uploading stats of each URL.
To achieve, it fetches data from redis w.r.t. master job and subtasks i.e. each URL tasks and celery job status,
later it prepares the response and return as json
'''
@app.route('/v1/images/upload/<string:jobId>', methods=['GET'])
def get_tasks(jobId):
	# validate the Job ID by fetching timestamp of given job
	ts = redisobj.get("imgur_create_ts_" + jobId)
	if ts is None:
		return jsonify({"error": "Provided 'jobID' does not exist."}), 400

	# success, failed lists init
	completed = []
	failed = []
	pending = []
	finished = None
	status = "pending"
	# fetching subtasks i.e. Celery Tasks' IDS assigned to get things uploaded for each URL
	lst_subtasks = redisobj.get("imgur_" + str(jobId))
	#preparing it in dict
	d_obj = json.loads(lst_subtasks)

	# for each task, need to fetch the status and details
	for ele in d_obj["subtasks"]:
		# check if task has been successful
		result = uploading_task.AsyncResult(str(ele["task_id"]))
		if result.state == "SUCCESS":
			completed.append(ele["url"])
		elif result.state == "FAILURE":
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
It fetches all the URLs from redis which are successfully uploaded
'''
@app.route('/v1/images', methods=['GET'])
def get_images():
	# fetching all the relevant keys from redis w.r.t. successful uploaded URL
	keys = redisobj.keys(pattern="imgur_subtask*")
	# Preparing list (for response)
	linkURLs = []

	# iter from each item
	for ele in keys:
		# appending the value i.e. final imgur URL
		linkURLs.append(redisobj.get(ele))

	#preparing the response
	res = {
		"uploaded" : linkURLs
	}
	# returning the response
	return jsonify(res), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
