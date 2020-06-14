#!flask/bin/python
from flask import Flask, jsonify
from flask import request
from celery import Celery
import settings
from celery import Celery
import requests
import uuid
import redis
import base64
from imgurpython import ImgurClient
import os

app = Flask(__name__)

app.config.from_object(settings)

# for in-mem storage
redisobj = redis.StrictRedis(host='localhost', port=6379, db=0)
# vars
localpath = app.config['LOCALFILEPATH']
client_id = None
client_secret = None

'''
Defining celery apply app context and app settings
'''
def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

# initialising celery
celery = make_celery(app)

'''
A master celery task to do a complete job of downloading, converting to base64 and uploading to imgur
'''
@celery.task(name="tasks.uploading_task")
def uploading_task(url, job_id):
	# fetching each URL and download the image from URL
	subtask = download(url)

	# check if download completed
	if subtask is not None:
		# uploading to imgur task
		subtask_upload = uploadtoImgur(subtask)
		# check if upload task been done successfully
		if subtask_upload is None:
			# upload failed, returning False signal
			return False
	else:
		return False
	# setting up the final link URL from imgur, this exectes only if success
	# preparing key as  "imgur_subtask_<taskID>" and Value as linkURL
	redisobj.set("imgur_subtask_" + uploading_task.request.id, subtask_upload)

	# removing the file from system
	removefile(subtask)

'''
This will download the image form URL
'''
def download(url):
	try:
		print('Beginning file download for (' + url + ') with requests') 
		# downloading content from URL 
		r = requests.get(url)
		# unique id to append in filename
		uniqueid = uuid.uuid1().hex
		# extracting filename from URL
		filename = uniqueid + "_" + url.split('/')[-1]

		with open(localpath + filename, 'wb') as f:  
		    f.write(r.content)
	except Exception as e:
		print "Something went wrong while downloading or storing file for url: %s" % url 
		return None

	print "Download complete for url: %s" % url 
	# Returning file if the download task is successfully done.
	return filename

'''
This will upload the image to Imgur, after converting it to base64
'''
def uploadtoImgur(file):
	# preparing filepath
	filepath = localpath + file

	encoded_string = ""
	# Converting Image file to base64
	with open(filepath, "rb") as image_file:
		encoded_string = base64.b64encode(image_file.read())

	# setup imgur lib params (include in ontime loading)
	client_id = app.config['CLIENT_ID']
	client_secret = app.config['CLIENT_SECRET']
	# Loading imgur lib cleint
	client = ImgurClient(client_id, client_secret)

	try:
		# uploads an image through lib:
		image = client.upload_from_path(filepath, config=None, anon=True) # anonymously
	except Exception as e:
		print "Something went wrong while uploading image from local to imgur (path: " + filepath + ")"
		# returning None if something goes bad while uploading
		return None

	#redisobj.set("imgur_")
	print "Uploaded successfully, link = " + image["link"]

	# returning image link URL if success
	return image["link"]

'''
Removes the file from system
This task should execute after the uploading to imgur is done in proper way
'''
def removefile(file):
	filepath = localpath + file
	try:
		os.remove(filepath)
	except OSError:
		print "Unable to remove file %s" % s
		return False

	return True


