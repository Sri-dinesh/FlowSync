# FlowSync - Smart Traffic Management Simulation

> **AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning**

FlowSync is a full-stack, real-time traffic simulation system where a Deep Q-Network (DQN) agent learns to optimize traffic signal control at a city intersection. Watch the AI learn to minimize vehicle wait times, compare its performance against traditional fixed-timer signals, and visualize everything in stunning 3D.

[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.7-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![Three.js](https://img.shields.io/badge/Three.js-0.184-000000?logo=three.js)](https://threejs.org/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com/)


## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)


## Overview

### What is FlowSync?

FlowSync demonstrates how reinforcement learning can optimize real-world traffic systems. The project simulates a 4-way intersection where:

- **Vehicles** arrive following a Poisson distribution
- **Traffic signals** control the flow through 4 phases (NS Green, EW Green, NS Left, EW Left)
- **A DQN agent** observes queue lengths and decides when to switch signals
- **Real-time visualization** shows the intersection in 3D using Three.js
- **Performance metrics** compare AI control vs traditional fixed-timer control

### Key User Flows

1. **Launch Simulation** - Watch live traffic flow in 3D
2. **Toggle Modes** - Switch between Fixed-Timer and AI-Controlled signals
3. **Train Agent** - Watch the DQN learn in real-time with live reward/loss charts
4. **Compare Performance** - See side-by-side metrics: AI vs Fixed-Timer
5. **Review History** - Browse past episodes, training runs, and model checkpoints


## Features

### Interactive Simulation
- **Real-time 3D visualization** using React Three Fiber
- **Live vehicle spawning** with configurable Poisson rates
- **Dynamic traffic signals** with realistic phase transitions
- **Queue visualization** showing waiting vehicles at each lane

### AI-Powered Control
- **Deep Q-Network (DQN)** agent with experience replay
- **Continuous learning** with epsilon-greedy exploration
- **Model checkpointing** to Supabase Storage
- **Live training metrics** streamed via WebSocket

### Analytics Dashboard
- **Real-time metrics**: avg wait time, throughput, queue lengths
- **Training charts**: reward curves, loss over episodes
- **Comparison view**: Fixed vs AI performance side-by-side
- **Episode history**: Browse all past simulation runs

### Real-Time Communication
- **WebSocket streams** for simulation frames (~10fps)
- **Training metrics** pushed live during agent learning
- **Persistent storage** of all episodes and metrics in PostgreSQL


## Tech Stack

### Frontend (client/)
- **Framework**: Next.js 16 (App Router), React 19, TypeScript
- **Styling**: Tailwind CSS v4, Shadcn/ui (Vercel theme)
- **3D Graphics**: Three.js via React Three Fiber, @react-three/drei
- **State Management**: Zustand (global state), TanStack Query (server state)
- **Animation**: Framer Motion
- **Package Manager**: pnpm

### Backend (server/)
- **Framework**: FastAPI 0.115, Uvicorn
- **ML/RL**: PyTorch 2.7, Gymnasium, NumPy
- **Database Client**: Supabase Python client (supabase-py)
- **Validation**: Pydantic v2
- **WebSockets**: websockets 12.0

### Database & Storage
- **Database**: Supabase PostgreSQL
- **ORM**: Prisma (client-side reads), supabase-py (server-side writes)
- **Storage**: Supabase Storage (model checkpoints)

### Deployment
- **Frontend**: Vercel
- **Backend**: Railway (Docker)
- **Database**: Supabase Cloud


## Getting Started

### Prerequisites

- **Node.js** 20+ and **pnpm** 9+
- **Python** 3.11+
- **Supabase** account (free tier works)
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/flowsync.git
cd flowsync
```

### 2. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Copy your project credentials:
   - `DATABASE_URL` (direct connection string)
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
3. Create a storage bucket named `model-checkpoints` (private)

### 3. Set Up the Frontend

```bash
cd client

# Install dependencies
pnpm install

# Create environment file
cp .env.example .env.local

# Edit .env.local with your Supabase credentials
# DATABASE_URL=postgresql://...
# NEXT_PUBLIC_SUPABASE_URL=https://...
# NEXT_PUBLIC_SUPABASE_ANON_KEY=...
# NEXT_PUBLIC_FASTAPI_WS_URL=ws://localhost:8000
# NEXT_PUBLIC_FASTAPI_HTTP_URL=http://localhost:8000

# Initialize database schema
pnpm prisma db push
pnpm prisma generate

# Start development server
pnpm dev
```

Frontend will be available at `http://localhost:3000`

### 4. Set Up the Backend

```bash
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env with your Supabase credentials
# SUPABASE_URL=https://...
# SUPABASE_SERVICE_KEY=...
# CORS_ORIGINS=http://localhost:3000

# Start development server
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

### 5. Verify Installation

1. Open `http://localhost:3000` in your browser
2. Check that the landing page loads
3. Navigate to the simulation page
4. Open `http://localhost:8000/docs` to see the FastAPI documentation


## Usage

### Running a Simulation

1. **Launch the app** and navigate to the simulation page
2. **Choose a mode**:
   - **Fixed Mode**: Traditional timer-based signals (30s green, 2s yellow)
   - **AI Mode**: DQN agent controls signals based on queue lengths
3. **Click "Start Simulation"** to begin
4. **Watch the 3D visualization** as vehicles spawn and move through the intersection
5. **Monitor metrics** in real-time: avg wait time, throughput, queue lengths

### Training the AI Agent

1. **Click "Train Agent"** in the training panel
2. **Watch live training metrics**:
   - Episode number and total reward
   - Average wait time per episode
   - Epsilon (exploration rate)
   - Loss values
3. **Training runs for 500 episodes** by default (configurable)
4. **Model checkpoints** are automatically saved to Supabase Storage
5. **View training progress** on the reward/loss charts

### Comparing Performance

1. **Run a simulation in Fixed Mode** → note the metrics
2. **Switch to AI Mode** → run another simulation
3. **Navigate to the Comparison Dashboard**
4. **View side-by-side metrics**:
   - Average wait time: Fixed vs AI
   - Throughput: Fixed vs AI
   - Improvement percentage
5. **Browse episode history** to see all past runs