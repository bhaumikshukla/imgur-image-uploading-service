import settings
import requests
import uuid
import base64
from imgurpython import ImgurClient
import os

# vars
localpath = settings.LOCALFILEPATH
client_id = None
client_secret = None

# Dict objects for storing status of each job and URLs
records = {} # this will store all the status related to master task and subtasks (each URL's uploading job)
imgur_urls_list = {} # This will store the final URL received from imgur

'''
A master celery task to do a complete job of downloading, converting to base64 and uploading to imgur
'''
def uploading_task(url, job_id, new_task_id):
	# fetching each URL and download the image from URL
	global records
	subtask = download(url)

	# check if download completed
	if subtask is not None:
		# uploading to imgur task
		subtask_upload = uploadtoImgur(subtask)
		# check if upload task been done successfully
		if subtask_upload is None:
			# upload failed, returning False signal
			records["imgur_subtask_status_" + new_task_id] = "FAILURE"
			return False
	else:
		records["imgur_subtask_status_" + new_task_id] = "FAILURE"
		return False
	# setting up the final link URL from imgur, this exectes only if success
	# preparing key as  "imgur_subtask_<taskID>" and Value as linkURL
	
	imgur_urls_list["imgur_subtask_result" + new_task_id] = subtask_upload
	records["imgur_subtask_status_" + new_task_id] = "SUCCESS"

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
	client_id = settings.CLIENT_ID
	client_secret = settings.CLIENT_SECRET
	# Loading imgur lib cleint
	client = ImgurClient(client_id, client_secret)

	try:
		# uploads an image through lib:
		image = client.upload_from_path(filepath, config=None, anon=True) # anonymously
	except Exception as e:
		print "Something went wrong while uploading image from local to imgur (path: " + filepath + ")"
		# returning None if something goes bad while uploading
		return None

	
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


