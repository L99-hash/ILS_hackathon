# NovaBoard Electronics Hackathon 2026 - Team 1

AI Production Scheduling Agent for PCB Manufacturing

## Overview

This project implements an intelligent production scheduling agent for NovaBoard Electronics, a contract PCB manufacturer. The agent reads sales orders, detects scheduling conflicts, proposes optimal solutions using deadline-based scheduling, and executes production through physical world integration.

## Mission

Build an AI agent that:
- Reads 12 open sales orders from the Arke system
- Detects and resolves scheduling conflicts intelligently
- Proposes solutions using Earliest Deadline First (EDF) scheduling
- Executes production through physical integration with the factory line

## Core Challenge

**The Scheduling Conflict:**
SmartHome IoT has escalated order SO-005 from P3 to P1 priority. However, SO-003 (AgriBot) has a deadline of March 4, which is tighter than SO-005's deadline of March 8. The agent must recognize this and schedule by deadline rather than blind priority.

## Factory Constraints

- **Single production line** - Sequential batch processing only
- **Capacity** - 480 minutes per day, 7 days per week
- **7 production phases** - SMT → Reflow → THT → AOI → Test → Coating → Pack
- **No parallelization** - All units must complete each phase before moving to the next

## Implementation Steps

### 1. Read Orders
Retrieve all accepted sales orders including:
- Product specifications
- Quantity
- Deadline
- Priority level

### 2. Choose Planning Policy
Decide on batching strategy:
- **Level 1:** One order per production order
- **Level 2:** Group by product or cap batch size for efficiency

### 3. Create Production Orders
Generate production orders in Arke with:
- Start and end dates
- Product and quantity mapping
- Resource allocation

### 4. Schedule Phases
- Call `_schedule` endpoint to generate phase sequences
- Assign concrete dates to each phase
- Ensure no conflicts with factory capacity

### 5. Human in the Loop
- Present schedule to planner via messaging
- Explain EDF reasoning for SO-005 prioritization
- Get approval before execution

### 6. Physical Integration (Camera Monitoring)
**Integrated into main workflow after Step 5**

Monitor production phases with live camera feed:
- Opens camera window showing production line
- Displays phase name, status, and timestamp overlay
- Saves frames every 10 seconds to `monitoring_frames/`
- Monitor all phases of all production orders sequentially
- Press 'q' to skip to next phase

**Automatically prompts after Step 5 approval**

### 7. Confirm & Execute
- Move orders to in_progress status
- Drive phase lifecycle through completion
- Track progress and handle exceptions

## API Endpoints

### Sales Orders
```
GET /api/sales/order?status=accepted
```
List all open sales orders awaiting production.

### Production Orders
```
PUT /api/product/production
```
Create a new production order with scheduling details.

### Scheduling
```
POST /production/{id}/_schedule
```
Generate phase sequence for a production order.

### Phase Management
```
POST /production-order-phase/{id}/_start
```
Start a specific production phase.

```
POST /production-order-phase/{id}/_complete
```
Mark a production phase as complete.

## Physical Integration

The system supports real-world factory integration through:
- **Line monitoring** - Camera-based detection of running/idle/fault states
- **Robot control** - Automated actuation for material handling
- **Status verification** - Real-time validation of production progress

## Quick Start

### 1. Create Conda Environment

```bash
conda env create -f environment.yml
conda activate novaboard-scheduling
```

### 2. Configure API Credentials

```bash
cp .env.example .env
```

The credentials are already set (username: arke, password: arke). 

### 3. Run Step 1: Read Sales Orders

```bash
python main.py
```

This will fetch all accepted sales orders and identify the SO-003 vs SO-005 scheduling conflict.

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Project Structure

```
ILS_hackathon/
├── README.md                    # This file
├── SETUP.md                     # Detailed setup guide
├── .gitignore                   # Git ignore rules
├── .env.example                 # Environment template
├── environment.yml              # Conda environment
├── requirements.txt             # Python dependencies
├── main.py                      # Main program entry point
├── src/
│   ├── api/
│   │   └── client.py           # Arke API client
│   ├── models/                 # Data models
│   └── scheduler/              # Scheduling algorithms
└── tests/                      # Test suite
```

## Technology Stack

- **Python 3.10** - Core programming language
- **Conda** - Environment management
- **requests** - HTTP client for API communication
- **pydantic** - Data validation and modeling
- **python-dotenv** - Environment configuration
- **pytest** - Testing framework

## Team

Team 1 - NovaBoard Electronics Hackathon 2026

## License

(To be determined)
