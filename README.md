# Multiplayer Bingo Game

A real-time multiplayer Bingo game built with WebSockets.

## Features

- **Real-time Gameplay**: Play against an opponent in real-time.
- **Turn-based System**: Players take turns marking numbers on the board.
- **Live Updates**: Game state, turns, and scores are updated instantly across connected clients.
- **Win Detection**: Automatic detection of completed lines and game winner.
- **Responsive UI**: Clean interface with visual indicators for turns and game status.

## Technologies Used

- **Frontend**: HTML, CSS (Tailwind CSS), JavaScript
- **Communication**: Socket.IO

## How to Play

1. Enter your username to join the game.
2. Wait for an opponent to join.
3. Once the game starts, players take turns selecting a number on the grid.
4. The selected number is marked on both players' boards.
5. The goal is to complete rows, columns, or diagonals (lines).
6. The first player to complete the required number of lines wins!

## Setup

1. Clone the repository.
2. Install dependencies (refer to backend documentation).
3. Start the server.
4. Open the application in your browser.

## Project Structure

- `static/`: Contains static assets like JavaScript and CSS.
- `templates/`: (Assumed) HTML templates.
- `app.py` / `server.js`: (Assumed) Backend server entry point.
