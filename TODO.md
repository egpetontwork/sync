# Docker Setup Tasks

- [x] Create Dockerfile for sync_core application
- [x] Create docker-compose.yml with Prefect server and Redis services
- [x] Configure networking and environment variables
- [ ] Test the setup

## Usage Instructions

1. Update the `.env` file with your actual vSphere credentials
2. Run `docker-compose up --build` to start all services
3. Access Prefect UI at http://localhost:4200
4. The core_sync service will automatically run the sync flow
