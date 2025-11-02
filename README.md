# Project: Elevator Sign Detection

This project is designed to detect elevator signs using a custom-trained YOLOv8 model. It includes a backend server for inference and a frontend for user interaction.

## Prerequisites

1. **Install Node.js**: Ensure you have Node.js installed. You can download it from [Node.js official website](https://nodejs.org/).
2. **Install Python**: Ensure Python 3.8+ is installed. You can download it from [Python official website](https://www.python.org/).
3. **Install Git**: Ensure Git is installed. You can download it from [Git official website](https://git-scm.com/).

## Setup Instructions

### 1. Clone the Repository
```bash
# Clone the repository to your local machine
git clone https://github.com/hsqsh/maisHack25.git
cd maisHack25
```

### 2. Set Up Python Environment
```bash
# Create and activate a virtual environment
python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

# Install Python dependencies
pip install -r models/requirements.txt
```

### 3. Set Up Frontend
```bash
# Navigate to the frontend directory
cd objectDetectorFE

# Install Node.js dependencies
npm install
```

### 4. Start Backend Server
```bash
# Navigate back to the project root
cd ..

# Start the backend server
.\.venv\Scripts\python.exe models\infer_server.py
```

### 5. Start Frontend
```bash
# Navigate to the frontend directory
cd objectDetectorFE

# Start the development server
npm run dev
```

### 6. Access the Application
- Open your browser and navigate to `http://localhost:5173` to use the application.

## Usage

1. **Frontend**:
   - Adjust settings like sensitivity and scan interval.
   - Start detection by clicking the "Record" button.
2. **Backend**:
   - The backend processes images and returns detection results.

## Troubleshooting

- **Port Conflicts**:
  - Ensure no other processes are using ports `8000` (backend) or `5173` (frontend).
  - Use `netstat -ano | findstr :8000` to check for processes using port `8000`.
- **Dependencies**:
  - Ensure all dependencies are installed correctly.
  - Use `pip list` and `npm list` to verify.
