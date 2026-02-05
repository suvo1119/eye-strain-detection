# 👁️ Eye Strain Monitoring System

A real-time eye strain detection and monitoring web application using MediaPipe face landmarks, Flask, and React.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![React](https://img.shields.io/badge/React-18.2+-61DAFB.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Real-time Eye Tracking** - Uses MediaPipe FaceLandmarker for accurate blink detection
- **Live Metrics Dashboard** - WebSocket-powered real-time metrics display
- **User Authentication** - Secure JWT-based login/register system
- **Profile Onboarding** - Collects user preferences (age, gender, glasses info)
- **Session-based Reports** - Tracks eye strain metrics per session and per day
- **Responsive Design** - Works on desktop and mobile devices

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **Flask** - Web framework
- **Flask-SocketIO** - Real-time WebSocket communication
- **Flask-JWT-Extended** - JWT authentication
- **SQLAlchemy** - ORM for database
- **MediaPipe** - Face landmark detection

### Frontend
- **React 18** - UI library
- **React Router v6** - Client-side routing
- **Socket.IO Client** - Real-time communication
- **TailwindCSS** - Styling
- **Vite** - Build tool

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/eye-strain-monitor.git
cd eye-strain-monitor
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r web-app/requirements.txt
```

3. **Install frontend dependencies**
```bash
cd web-app
npm install
```

4. **Start the backend**
```bash
python flask_api.py
```

5. **Start the frontend (in a new terminal)**
```bash
npm run dev
```

6. **Open your browser**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## 🌐 Deployment on Railway

### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Manual Deployment

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

3. **Deploy**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect the configuration

4. **Set Environment Variables** (in Railway dashboard)
```
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
```

5. **Your app is live!** 🎉

## 📁 Project Structure

```
eye-strain-monitor/
├── web-app/
│   ├── flask_api.py          # Main Flask application
│   ├── database.py           # SQLAlchemy models
│   ├── auth_routes.py        # Authentication endpoints
│   ├── reports_routes.py     # Reports API endpoints
│   ├── requirements.txt      # Python dependencies
│   ├── Procfile             # Railway deployment config
│   ├── railway.json         # Railway settings
│   ├── package.json         # Node.js dependencies
│   ├── vite.config.js       # Vite configuration
│   └── src/
│       ├── App.jsx          # Main React component
│       ├── index.css        # Global styles
│       ├── contexts/
│       │   └── AuthContext.jsx
│       └── pages/
│           ├── LoginPage.jsx
│           ├── RegisterPage.jsx
│           ├── ProfileSetup.jsx
│           └── ReportsDashboard.jsx
└── README.md
```

## 📊 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/profile` | Update user profile |
| POST | `/api/auth/logout` | Logout user |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/dashboard` | Get dashboard stats |
| GET | `/api/reports/sessions` | Get session-based reports |
| POST | `/api/reports/save` | Save eye strain data |

### WebSocket Events
| Event | Direction | Description |
|-------|-----------|-------------|
| `start_monitoring` | Client → Server | Start eye tracking |
| `stop_monitoring` | Client → Server | Stop eye tracking |
| `metrics_update` | Server → Client | Real-time metrics |
| `blink_alert` | Server → Client | Blink rate warning |

## 🔒 Security

- Passwords hashed with bcrypt
- JWT tokens for authentication
- CORS configured for allowed origins
- Environment variables for secrets

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | (required) |
| `JWT_SECRET_KEY` | JWT signing key | (required) |
| `DATABASE_URL` | Database connection URL | sqlite:///eye_strain.db |
| `PORT` | Server port | 5000 |

## 📄 License

MIT License - feel free to use this project for learning and personal projects.

## 👨‍💻 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/yourprofile)

---

⭐ Star this repo if you found it helpful!
