# Student Scheduler – OR-Tools Optimization Engine

![CI/CD](https://github.com/JonSnow1807/student-scheduler/workflows/CI/CD%20Pipeline/badge.svg)
![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)
![OR-Tools](https://img.shields.io/badge/OR--Tools-v9.8-green.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)

## Overview

AI-powered course scheduling system that optimizes timetables for 500+ students using Google OR-Tools constraint programming. This system solves a complex constraint satisfaction problem, eliminating scheduling conflicts while maximizing student preferences.

## 🎯 Key Achievements

- **100% Schedule Coverage**: Successfully scheduled all 500 students
- **0% Time Conflicts**: Eliminated scheduling conflicts (vs 70% baseline)
- **90% Satisfaction Rate**: Achieved high preference fulfillment
- **60-Second Processing**: Optimized 500 students in under a minute
- **Production-Ready**: Containerized with Docker & Kubernetes configs

## 🛠 Tech Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Optimization Engine**: Google OR-Tools CP-SAT Solver
- **Database**: PostgreSQL 15
- **Caching**: Redis 7
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes (with HPA for auto-scaling)
- **CI/CD**: GitHub Actions
- **Cloud Ready**: Configured for OCI deployment

## 📊 Performance Metrics

Based on actual testing with 500 students:

| Metric | Value |
|--------|-------|
| Students Scheduled | 500/500 (100%) |
| Total Course Assignments | 1,880 |
| Average Courses/Student | 3.76 |
| Optimization Time | 60.9 seconds |
| Solver Branches Explored | 101,441 |
| Time Conflicts | 0 |
| Overall Satisfaction | 89.9% |

### Satisfaction by Priority Level
- **Priority 1**: 498/500 (99.6%)
- **Priority 2**: 498/500 (99.6%)
- **Priority 3**: 473/500 (94.6%)
- **Priority 4**: 234/344 (68.0%)
- **Priority 5**: 104/167 (62.3%)

[View Full Metrics](full_metrics.json)

## 🔧 How It Works

1. **Input**: Students submit ranked course preferences (1-5 priority)
2. **Modeling**: System creates binary decision variables x[student,course]
3. **Constraints**: 
   - No time conflicts (students can't be in two places)
   - Course capacity limits
   - Student course load (3-5 courses)
4. **Optimization**: OR-Tools explores 100K+ solution branches
5. **Output**: Conflict-free schedule maximizing preferences

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum (for OR-Tools optimization)
- Port 5002 available

### Local Development

```bash
# Clone repository
git clone https://github.com/JonSnow1807/student-scheduler.git
cd student-scheduler

# Run with Docker Compose
docker-compose up -d

# Wait for services to start (check logs)
docker-compose logs -f

# Seed database with test data (500 students)
docker-compose exec web python seed_data.py

# Run optimization
curl -X POST http://localhost:5002/api/schedules/optimize \
  -H "Content-Type: application/json" \
  -d '{"semester": "Spring2024"}'

## 🩺 Health Check

```bash
# Verify system is running
curl http://localhost:5002/health
# Expected: {"status": "healthy"}

# Check database connection
curl http://localhost:5002/ready
# Expected: {"status": "ready"}


## Core Endpoints

### Run Schedule Optimization
```bash
POST /api/schedules/optimize
Content-Type: application/json

{
  "semester": "Spring2024"
}

# Response (after ~60 seconds)
{
  "status": "success",
  "schedules_created": 1880,
  "metrics": {
    "students_scheduled": 500,
    "conflict_rate": 0.0,
    "satisfaction_rate": 89.9
  }
}

### Get Student Schedule
```bash
GET /api/schedules/student/{student_id}

# Response
[
  {
    "course": "Data Structures",
    "course_code": "CS201",
    "day": 0,
    "start_time": "10:00:00",
    "end_time": "11:30:00",
    "room": "Room 101"
  },
  ...
]
### View Optimization Metrics
```bash
GET /api/schedules/metrics/{semester}

# Returns comprehensive metrics including:
# - Satisfaction by priority
# - Course utilization
# - Conflict analysis
# - Solver performance stats

## 🏗 Architecture
```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Flask API     │────▶│   OR-Tools      │────▶│   PostgreSQL    │
│   (REST)        │     │   Optimizer     │     │   Database      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               │
         ▼                                               ▼
┌─────────────────┐                            ┌─────────────────┐
│                 │                            │                 │
│     Redis       │                            │   SQLAlchemy    │
│     Cache       │                            │      ORM        │
│                 │                            │                 │
└─────────────────┘                            └─────────────────┘

## 📈 OR-Tools Implementation Details

### Decision Variables
```python
x[s, c] = BoolVar()  # 1 if student s is assigned course c

### Constraints
```python
# Time conflicts
sum(x[s, c] for c in conflicting_courses) <= 1

# Course capacity
sum(x[s, c] for s in students) <= course.capacity

# Student load
3 <= sum(x[s, c] for c in courses) <= 5

### Objective Function
```python
maximize sum(weight[priority] * x[s, c] for all assignments)
# where weight = {1: 10, 2: 6, 3: 3, 4: 1, 5: 0}

## 🐳 Docker Configuration
The application runs three containerized services:

- **web** : Flask application with Gunicorn  
- **db**  : PostgreSQL 15 database  
- **redis** : Redis cache for performance  

```yaml
# Key service configuration
web:
  build: .
  ports:
    - "5002:5000"
  environment:
    - DATABASE_URL=postgresql://postgres:password@db/student_scheduler

## ☸️ Kubernetes Deployment
Production-ready Kubernetes manifests included:

- **Deployment** : 3 replicas with health checks  
- **Service**  : LoadBalancer for external access  
- **HPA**      : Auto-scaling based on CPU / memory  
- **ConfigMap / Secrets** : Environment configuration  

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n production
kubectl get svc  -n production

## 🧪 Testing
```bash
# Run unit tests
docker-compose exec web pytest tests/ -v

# Run tests with coverage report
docker-compose exec web pytest tests/ --cov=app --cov-report=html

## 📋 Project Structure
```text
student-scheduler/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   └── utils/               # Helper functions
├── k8s/                     # Kubernetes manifests
├── tests/                   # Unit tests
├── docker-compose.yml       # Local development
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── seed_data.py             # Test data generator


## 🔍 Algorithm Insights
- Explored **101,441** solution branches  
- Made smart trade-offs (e.g., bumping some students from priority 2 to 3)  
- Achieved **zero conflicts** while maintaining high satisfaction  
- Found a near-optimal solution within a **60-second** timeout  

---

## 🚦 CI/CD Pipeline (GitHub Actions)
- Automated testing with **pytest**  
- Code linting (**Black**, **Flake8**)  
- Docker image building  
- Deployment to **OCI** registry  
- Kubernetes rollout  

---

## 📝 Environment Variables
Create a `.env` file for local development:

```env
DATABASE_URL=postgresql://postgres:password@localhost/student_scheduler
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
FLASK_ENV=development


## 🤝 Contributing
```bash
# Fork the repository and create your feature branch
git checkout -b feature/AmazingFeature

# Commit your changes
git commit -m "Add some AmazingFeature"

# Push to the branch
git push origin feature/AmazingFeature

## 📄 License
This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments
- **Google OR-Tools** team for the excellent constraint-programming solver  
- **Flask** community for the robust web framework  
- **Docker & Kubernetes** for containerization and orchestration  
