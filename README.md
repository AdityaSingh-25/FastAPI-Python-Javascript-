
# FastAPI + JavaScript Full Stack Application

## Overview

This project is a full stack web application built using FastAPI for the backend and JavaScript for the frontend. It demonstrates the development of RESTful APIs, database integration, and a simple user interface for interacting with backend services.

The application is designed to showcase backend API design, data handling, and frontend integration in a scalable and modular structure.

---

## Features

* REST API built with FastAPI
* CRUD operations for data management
* Database integration
* Frontend interface for interacting with APIs
* Modular and scalable project structure

---

## Tech Stack

**Backend**

* FastAPI
* Python

**Frontend**

* JavaScript
* HTML / CSS

**Database**

* SQLite (or configured database)

**Tools**

* Git and GitHub for version control

---

## Project Structure

```
FastAPI-Python-Javascript/
│
├── main.py                 # Entry point of FastAPI app
├── database.py             # Database connection setup
├── database_models.py      # Database schema/models
├── models.py               # Pydantic models
│
├── frontend/               # Frontend application
│   ├── public/
│   └── src/
│
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

* Python 3.8+
* Node.js (if frontend requires build tools)
* pip

---

### Backend Setup

```bash
# Create virtual environment
python -m venv myenv

# Activate environment
source myenv/bin/activate  # Mac/Linux
myenv\Scripts\activate     # Windows

# Install dependencies
pip install fastapi uvicorn

# Run server
uvicorn main:app --reload
```

Backend will run on:

```
http://127.0.0.1:8000
```

API docs available at:

```
http://127.0.0.1:8000/docs
```

---

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

---

## API Endpoints

| Method | Endpoint    | Description  |
| ------ | ----------- | ------------ |
| GET    | /           | Health check |
| GET    | /items      | Fetch items  |
| POST   | /items      | Create item  |
| PUT    | /items/{id} | Update item  |
| DELETE | /items/{id} | Delete item  |

---

## Future Improvements

* Add authentication and authorization
* Deploy backend and frontend
* Add logging and monitoring
* Improve UI/UX
* Integrate advanced analytics

---

## Author

Aditya Singh

---

## License

This project is open source and available under the MIT License.
