# Advanced Distributed Task Scheduler

This project implements an advanced distributed task scheduler built with FastAPI, PostgreSQL, SQLAlchemy, and machine learning models (using `joblib` and `scikit-learn`). It supports multiple worker nodes that execute tasks based on priority, and uses OAuth2 for user authentication with JWT tokens for security.

## Features

- **Task Management**: Users can create, retrieve, and complete tasks.
- **Distributed Workers**: Tasks are assigned to multiple worker nodes, which execute them asynchronously based on priority.
- **Priority Prediction**: An integrated machine learning model predicts task priority based on user and task features.
- **Authentication**: Secure user authentication using OAuth2 and JWT.
- **PostgreSQL Database**: Tasks and user data are persisted in a PostgreSQL database.
- **Dockerized Setup**: Uses Docker Compose to easily set up the task manager, worker nodes, and database.

## Architecture

The project consists of three main components:

1. **Core Service (Task Manager)**: This service handles task creation, prioritization using an ML model, and assigns tasks to worker nodes. It also manages user authentication.
2. **Worker Nodes**: These services execute tasks based on priority. Multiple worker nodes can run in parallel, allowing for distributed task execution.
3. **PostgreSQL Database**: A PostgreSQL database is used to store tasks and user information.

![Architecture Diagram](./docs/architecture.png) *(optional image)*

## Requirements

- **Python 3.9+**
- **Docker & Docker Compose**
- **PostgreSQL**

## Installation

cd advanced-distributed-task-scheduler
Set Up Environment Variables

Create a .env file in the root directory to store sensitive information:

SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@db/taskdb

Build and Run with Docker Compose

docker-compose up --build
This will start the following services:

Task Manager on http://localhost:8000
Worker Nodes on http://localhost:8001, http://localhost:8002, http://localhost:8003
PostgreSQL database
Migrate the Database
After the services are up, connect to the taskmanager container and run the database migrations:

docker-compose exec taskmanager alembic upgrade head
API Usage
Authentication
Obtain a JWT access token by sending a POST request to /token with a username and password:

POST http://localhost:8000/token

Creating a Task
To create a task, send a POST request to /tasks with a JSON body containing task details. The task will be assigned a priority and scheduled for execution by a worker node.


POST http://localhost:8000/tasks

Example JSON body:
json
{
  "name": "Example Task",
  "description": "This is an example task."
}
Retrieving a Task
To retrieve the status of a specific task, send a GET request to /tasks/{task_id}:

GET http://localhost:8000/tasks/1

Completing a Task
To mark a task as completed, send a PUT request to /tasks/{task_id}/complete:

bash
Copy code
PUT http://localhost:8000/tasks/1/complete
Priority Prediction
The task manager uses a machine learning model to predict task priority based on simplified task features (e.g., task name length, description length, user ID). The ML model is pre-trained and loaded using joblib. You can replace the model with your own by retraining it and saving it as priority_model.joblib.

Worker Nodes
Worker nodes are responsible for executing tasks. They simulate task execution by sleeping for a duration that is inversely proportional to the task's priority (higher priority tasks are executed faster).

Adding More Worker Nodes
To scale the system, simply add more worker node services to the docker-compose.yml file. Each worker node runs on a separate port and can handle tasks in parallel.

Testing
You can test the system using API tools like Postman or cURL. Automated testing can be set up using pytest and other testing frameworks. To ensure robustness, write unit tests for the API endpoints and critical functions.

Contributing
Contributions are welcome! If you have any ideas, bug reports, or feature requests, feel free to open an issue or submit a pull request.

Fork the repository
Create a feature branch (git checkout -b feature/my-feature)
Commit your changes (git commit -m 'Add my feature')
Push to the branch (git push origin feature/my-feature)
Open a pull request
License
This project is licensed under the MIT License. See the LICENSE file for more details.

Author
Ronak Banthia
Feel free to reach out for any questions or feedback!
