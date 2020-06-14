# Imgur image uploading service

This service is written in Python. 

It's a backend service which provides REST API interface to upload images to Imgur. Moreover, it provides set of APIs to check the progress and list all uploaded images with URL.

There are two relevant solutions been prepared here:


## Solution 1: Thread worker based

Here each subtask spawn a thread to do a specific job i.e. downloading from source and uploading to destination. It's a pure asynchronous behaviour of app.


### Flow
![Working flow](http://bshukla.com/imgur-app-sol1.png)

### Requirement
1. **Pyhton 2.7+**

2. [**Flask**](http://flask.pocoo.org/) Python based framework to develop REST APIs & web services

This is pure python based applicaiton, no external storage and in-memory data store been used. It uses internal Dict to store all the data within the application (in-memory).


## Installation
If you don't have python, please install python 2.7 and pyhton-pip. (one of the way to install python as follows:
```
sudo add-apt-repository ppa:fkrull/deadsnakes
sudo apt-get update
sudo apt-get install python2.7
sudo apt-get install python-pip

```
### Install Application requirements

It's recommended to use **virtualenv** for python based project dependencies to keep isolation.


```
cd solution1-threadworker
pip install -r requirement.txt
```
This will install all python specific dependencies of the project.

## RUN
It's a simple python application runs normally as follows:
```
python app.py
```

### Flow description:

* **POST /v1/images/upload** : It fetches the URLs from request and assign separate uploading tasks (Thread based worker jobs) for each URL map it with master job ID.
* **GET /v1/images/upload/[jobId]>**:  It fetches the provided URL from request, gather all the data w.r.t. the master jobID from in-memory Dict, status of each upload tasks, etc. Prepare the response and return the response.
* **GET /v1/images** : It simply gather all the final uploaded URLs of imgur (from all the successful tasks, stored in in-memory Dict) fetches details, prepare the response and return.


## How it runs (Behave similarly for both solutions):
Following GIF will showcase the usage how it executes and upload images in background jobs:

GIF

![How it works](http://bshukla.com/myimage_op.gif)





----------------------------------------------------------------------------
----------------------------------------------------------------------------



## Solution 2: Celery worker based, and Redis as in-mem storage

### Flow
![Working flow](http://bshukla.com/imgur-app.png)

### Requirement
 
**Pyhton 2.7+**

[**Celery**](http://www.celeryproject.org/) (Python based Distributed Task Queue/executor, 
it provides python based background workers & keep track of each jobs)

**Redis** (Used by Celery as in-memory storage for bg-tasks, also used by this application to store data in-memory as Key-Value pair)

[**Flask**](http://flask.pocoo.org/) Python based framework to develop REST APIs & web services


## Installation

If you don't have python, please install python 2.7 and pyhton-pip. (one of the way to install python as follows:
```
sudo add-apt-repository ppa:fkrull/deadsnakes
sudo apt-get update
sudo apt-get install python2.7
sudo apt-get install python-pip

```

Redis installation

```
sudo apt-get install redis-server
```

### Install Application requirements

It's recommended to use **virtualenv** for python based project dependencies to keep isolation.


```
cd solution2-celeryworker
pip install -r requirement.txt
```
This will install all python specific dependencies of the project.

## RUN
Following steps you need to execute to run the application as this application has two parts:
1. Celery worker: Where tasks are specified in task.py
2. Application which hosts REST endpoints

#### Run Celery worker
To start the celery worker following command needs to execute seperately:
```
celery -A task.celery worker --loglevel=info
```
This will start the worker and you may see similar output as follows:

```
(env_imgur) bhaumik@AHMLPT0636:~/imgur-image-uploading-service$ celery -A task.celery worker --loglevel=info
 
 -------------- celery@AHMLPT0636 v4.1.0 (latentcall)
---- **** ----- 
--- * ***  * -- Linux-4.4.0-103-generic-x86_64-with-Ubuntu-16.04-xenial 2018-01-27 01:48:31
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         task:0x7f2dfeb2f350
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 4 (prefork)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery
                

[tasks]
  . tasks.uploading_task

[2018-01-27 01:48:31,830: INFO/MainProcess] Connected to redis://localhost:6379/0
[2018-01-27 01:48:31,840: INFO/MainProcess] mingle: searching for neighbors
[2018-01-27 01:48:32,861: INFO/MainProcess] mingle: all alone
[2018-01-27 01:48:32,872: INFO/MainProcess] celery@AHMLPT0636 ready.
```

#### Run Applicaiton

To run the applicaiton, it's simple, just run python file as follows:
```
python app.py
```

This will generate following  output (similar as it runs under debug mode):

```
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 229-121-953

```


## Live Demo
Backend service is hosted here : http://163.172.131.17:5000

You can execute Following APIs

* http://163.172.131.17:5000/v1/images/upload - POST For submitting Image URLs for upload
* http://163.172.131.17:5000/v1/images/upload/28748e60-032d-11e8-8f46-0007cb03455e - GET upload job status
* http://163.172.131.17:5000/v1/images - GET list of all uploaded image links


#### APIs

##### 1. Submit Image URL for upload 
```
Method: POST
URL: /v1/images/upload
Request Body:
{
"urls":[
"https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg",
  "https://farm3.staticflickr.com/2879/11234651086_681b3c2c00_b_d.jpg"
]
}
```

Response:
```
{
    "jobId": "aca66440-032f-11e8-8f46-0007cb03455e"
}
```

##### 2. GET upload job status

```
Method: GET
URL: /v1/images/upload/<jobId>
Request Body: None
```

Example: [http://163.172.131.17:5000/v1/images/upload/aca66440-032f-11e8-8f46-0007cb03455e](http://163.172.131.17:5000/v1/images/upload/aca66440-032f-11e8-8f46-0007cb03455e)


##### 3. GET list of all uploaded image links
```
Method: GET
URL: /v1/images
Request Body: None
```

Example: [http://163.172.131.17:5000/v1/images](http://163.172.131.17:5000/v1/images)


## Note
Following tools/libs been used to achieve specific tasks

#### Flask
To bring up REST based applicaiton having few set of simple APIs.

#### Celery
For background asynchronous tasks. Flask app assigns each URL upload as separate task to celery worker, celery worker execute those tasks asynchronously in background and updates the status.

#### imgurpython
Used imgur official lib to upload images to imgur. We can also use their REST APIs as well.

#### uuid
UUID lib to generate unique ID for uploading job and uniquefilename generation.

#### base64
To convert images in base64 for uploading to imgur

#### redis
Redis lib to connect and work with hosted redis.

#### os
built-in os lib to work with system folder structure. Used to remove unnecessary images after being uploaded.


### Flow description:

* **POST /v1/images/upload** : It fetches the URLs from request and assign separate uploading tasks (Celery worker jobs) for each URL map it with master job ID.
* **GET /v1/images/upload/[jobId]>**:  It fetches the provided URL from request, gather all the data w.r.t. the master jobID from redis and celery like subtask (celery jobs), status of each upload tasks, etc. Prepare the response and return the response.
* **GET /v1/images** : It simply gather all the final uploaded URLs of imgur (from all the successful tasks, stored in redis) fetches details, prepare the response and return.


 
 
 
