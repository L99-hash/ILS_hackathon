# Setup Guide

This guide will help you set up the NovaBoard Electronics AI Production Scheduling Agent.

## Prerequisites

Before you begin, ensure you have the following installed:
- Conda (Anaconda or Miniconda)
- Python 3.10 (will be installed via conda)
- Git
- API access credentials for the Arke system
- Access to the factory line integration systems (camera, robot controller)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ILS_hackathon
```

### 2. Create Conda Environment

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate novaboard-scheduling
```

Alternatively, if you prefer using pip:

```bash
conda create -n novaboard-scheduling python=3.10
conda activate novaboard-scheduling
pip install -r requirements.txt
```

### 3. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

The `.env` file is already configured with the correct credentials:

```bash
# Arke API Configuration
# Team 1 endpoint (change number for your team: hackathon1 to hackathon60)
ARKE_API_BASE_URL=https://hackathon1.arke.so/api
ARKE_USERNAME=arke
ARKE_PASSWORD=arke

# Factory Configuration
FACTORY_CAPACITY_MINUTES=480
FACTORY_DAYS_PER_WEEK=7

# Physical Integration
CAMERA_ENDPOINT=<camera-api-url>
ROBOT_CONTROLLER_ENDPOINT=<robot-api-url>

# Messaging Configuration (for Human-in-Loop)
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=<your-bot-token-here>
TELEGRAM_CHAT_ID=<your-chat-id-here>

# Logging
LOG_LEVEL=INFO
```

### Telegram Bot Setup

To receive production schedule notifications on Telegram:

1. **Create a Telegram Bot:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` command
   - Follow prompts to name your bot
   - Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
   - Add this token to `.env` as `TELEGRAM_BOT_TOKEN`

2. **Get Your Chat ID:**
   - Start a conversation with your new bot
   - Send any message to the bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for the `"chat":{"id":...}` field in the JSON response
   - Copy the chat ID (e.g., `123456789`)
   - Add this to `.env` as `TELEGRAM_CHAT_ID`

3. **Test the Integration:**
   ```bash
   # Run the main.py script and proceed to Step 5
   # You should receive a schedule notification in your Telegram chat
   ```

## Configuration

### API Endpoints

Ensure the following API endpoints are accessible:

- **Sales Orders:** `GET /api/sales/order?status=accepted`
- **Production Orders:** `PUT /api/product/production`
- **Scheduling:** `POST /production/{id}/_schedule`
- **Phase Start:** `POST /production-order-phase/{id}/_start`
- **Phase Complete:** `POST /production-order-phase/{id}/_complete`

### Factory Phase Configuration

The system expects 7 production phases in this order:
1. SMT (Surface Mount Technology)
2. Reflow
3. THT (Through-Hole Technology)
4. AOI (Automated Optical Inspection)
5. Test
6. Coating
7. Pack

## Running the Application

### Development Mode

#### Python:
```bash
python main.py
```

#### Node.js:
```bash
npm run dev
```

### Production Mode

#### Python:
```bash
python main.py --production
```

#### Node.js:
```bash
npm start
```

## Testing

### Run Unit Tests

#### Python:
```bash
pytest tests/
```

#### Node.js:
```bash
npm test
```

### Run Integration Tests

```bash
# Test API connectivity
./scripts/test_api_connection.sh

# Test scheduling algorithm
./scripts/test_scheduler.sh
```

## Usage

### Basic Workflow

1. **Fetch Sales Orders:**
   ```bash
   # The agent will automatically fetch accepted sales orders
   ```

2. **Review Scheduling Conflicts:**
   ```bash
   # The agent identifies conflicts and proposes EDF-based solutions
   ```

3. **Approve Schedule:**
   ```bash
   # Human planner receives notification and approves the schedule
   ```

4. **Execute Production:**
   ```bash
   # The agent creates production orders and manages phase lifecycle
   ```

## Physical Integration Setup

### Camera Integration

Configure the camera system for line monitoring:

```bash
# Test camera connection
curl -X GET <camera-endpoint>/status

# Expected states: running, idle, fault
```

### Robot Controller Integration

Configure the robot controller for material handling:

```bash
# Test robot connection
curl -X POST <robot-endpoint>/test

# Verify actuation capabilities
```

## Troubleshooting

### Common Issues

**API Connection Errors:**
- Verify API credentials in `.env`
- Check network connectivity to Arke system
- Ensure API endpoints are correct

**Scheduling Conflicts:**
- Review factory capacity settings
- Check phase duration configurations
- Verify deadline and priority data

**Physical Integration Failures:**
- Test camera and robot endpoints independently
- Check firewall and network settings
- Verify hardware is powered and connected

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f logs/application.log
```

## Support

For issues and questions:
- Check the main [README.md](README.md)
- Review API documentation
- Contact the hackathon organizers

## Next Steps

1. Implement the scheduling algorithm
2. Set up API client for Arke system
3. Integrate messaging system for human-in-loop
4. Connect physical integration endpoints
5. Test end-to-end workflow with sample data
